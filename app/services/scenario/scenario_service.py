import time
import asyncio
import logging
import uuid
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel

from app.models.schemas.scenario import ScenarioResult, ScenarioSkeleton, ScenarioExpansion
from app.models.schemas.suspect import SuspectGenerationRequest, SuspectSchema
from app.models.schemas.suspect.response import SuspectGenerationListSchema
from app.models.schemas.clue.response import ClueSetSchema
from app.models.schemas.map.skeleton import MapSkeletonSchema
from app.models.schemas.map.detail import MapOutputSchema, RoomFurnitureSchema
from app.services.agent.clearability_evaluator import ClearabilityEvaluator
from app.services.agent.clue_generator import ClueGenerator
from app.services.agent.map_generator import MapGenerator
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.scenario_generator import ScenarioGenerator
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.agent.critic import ScenarioRefiner, RegenLevel
from app.services.llm.llm_client import LLMClient
from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.rag import get_rag_service
from app.core.json_retry import JSONParseRetry
from app.services.scenario.scenario_generate_helper import inject_sequential_id
from app.services.scenario.scenario_state_manager import ScenarioStateManager


logger = logging.getLogger(__name__)

# Max times we'll regenerate skeleton/expansion due to critic failures
MAX_CRITIC_REGEN = 2
# Max times we'll regenerate the full scenario due to clearability failures
MAX_CLEARABILITY_REGEN = 2


class ScenarioService:

    def __init__(self, llm_client: LLMClient):
        """
        Initialize ScenarioService with dependency injection.

        Parameters
        ----------
        llm_client : LLMClient
            LLM client instance (e.g., GeminiClient)
        """
        self.scenario_generator = ScenarioGenerator(llm_client)
        self.clue_generator = ClueGenerator(llm_client)
        self.map_generator = MapGenerator(llm_client)
        self.suspect_generator = SuspectGenerator(llm_client)
        self.validator = ConsistencyValidator()
        self.refiner = ScenarioRefiner(llm_client)
        self.clearability_evaluator = ClearabilityEvaluator(llm_client)
        self.repository = ScenarioRepository()
        self.rag_service = get_rag_service()

        # JSON 재시도 정책
        self.json_retry = JSONParseRetry(
            max_attempts=3,
            backoff_seconds=2.0,
            backoff_multiplier=1.5  # 2초 → 3초 → 4.5초
        )

        self.state_manager = ScenarioStateManager()

    def _load_or_generate(
        self,
        request_id: str,
        step_name: str,
        generator_func: Callable[[], Any],
        schema_name: str,
        model_type: Optional[Type[BaseModel]] = None,
        use_retry: bool = True,
        generator=None,
    ) -> Any:
        """Load a cached intermediate result or generate it.

        Parameters
        ----------
        request_id : str
            Request ID for state persistence.
        step_name : str
            Name of the generation step (used as cache key).
        generator_func : Callable
            Function that generates the result (called only on cache miss).
        schema_name : str
            Human-readable name for error messages.
        model_type : Type[BaseModel], optional
            Pydantic model to parse cached JSON into.
        use_retry : bool
            Whether to wrap generation in JSONParseRetry.

        Returns
        -------
        tuple[Any, bool]
            (result, was_generated) — was_generated is True if LLM was called.
        """
        cached = self.state_manager.load_intermediate_state(
            request_id, step_name, model_type
        )
        if cached is not None:
            logger.info(f"Loaded {step_name} from intermediate file.")
            return cached, False

        if use_retry:
            result = self.json_retry.parse_with_retry(
                parser_func=generator_func,
                schema_name=schema_name,
                generator=generator,
            )
        else:
            result = generator_func()

        if result is None:
            raise RuntimeError(f"{schema_name} generation failed after retries")

        self.state_manager.save_intermediate_state(request_id, step_name, result)
        return result, True

    def _sleep_if_generated(self, was_generated: bool, seconds: float = 3):
        """Sleep only when an LLM call was actually made (rate-limit throttle)."""
        if was_generated:
            time.sleep(seconds)

    def generate(self,
                 pre_input: str,
                 request_id: str = None) -> ScenarioResult:

        if request_id is None:
            request_id = str(uuid.uuid4())

        # 생성 시작
        # 1. 평서문 생성
        case_state, generated = self._load_or_generate(
            request_id, "case_state",
            lambda: self.scenario_generator.generate_case(pre_input),
            "CaseState", use_retry=False,
        )

        self._sleep_if_generated(generated)

        # 2-3. Skeleton → Expansion → Critic 평가 루프
        expansion_result = self._generate_and_validate_expansion(
            case_state, request_id
        )

        # 4-9. Generate content and validate clearability
        final_scenario = self._generate_content_with_clearability_check(
            expansion_result, request_id
        )

        return final_scenario

    def _generate_content_with_clearability_check(
        self,
        expansion_result: ScenarioExpansion,
        request_id: str,
    ) -> ScenarioResult:
        """Generate map/suspects/clues and validate clearability.

        If the clearability check fails, keeps the map (unlikely cause) and
        regenerates only suspects and clues with targeted feedback from the
        evaluator, saving ~2 LLM calls per retry.

        Parameters
        ----------
        expansion_result : ScenarioExpansion
            The validated expansion to build content from.
        request_id : str
            Request ID for state persistence.

        Returns
        -------
        ScenarioResult
            A clearability-validated final scenario.

        Raises
        ------
        RuntimeError
            If scenario is not clearable after all retry attempts.
        """
        clearability_feedback: str = ""

        for attempt in range(MAX_CLEARABILITY_REGEN + 1):
            if attempt > 0:
                logger.info(
                    f"Clearability regen attempt {attempt}/{MAX_CLEARABILITY_REGEN} "
                    f"— regenerating suspects + clues with feedback"
                )
                # Only clear suspects and clues; keep map_skeleton and map_detail
                self.state_manager.clear_intermediate_state(
                    request_id, "suspects_result"
                )
                self.state_manager.clear_intermediate_state(
                    request_id, "clue_result"
                )

            final_scenario = self._generate_content(
                expansion_result, request_id,
                clearability_feedback=clearability_feedback,
            )

            # 9. Clearability evaluation
            logger.info("Starting clearability evaluation...")
            scenario_data = final_scenario.model_dump(mode="json")
            evaluation = self.clearability_evaluator.evaluate(scenario_data)

            # Save clearability evaluation result
            self.state_manager.save_intermediate_state(
                request_id,
                f"clearability_eval_attempt{attempt}",
                evaluation,
            )

            if evaluation.is_clearable:
                logger.info("Scenario passed clearability check.")
                return final_scenario

            logger.warning(
                f"Scenario failed clearability check: {evaluation.reason[:300]}"
            )
            if attempt >= MAX_CLEARABILITY_REGEN:
                break

            # Pass evaluator feedback to next generation attempt
            clearability_feedback = evaluation.reason
            time.sleep(3)

        raise RuntimeError(
            f"Scenario is not clearable after {MAX_CLEARABILITY_REGEN + 1} attempts. "
            f"Last reason: {evaluation.reason}"
        )

    def _generate_content(
        self,
        expansion_result: ScenarioExpansion,
        request_id: str,
        clearability_feedback: str = "",
    ) -> ScenarioResult:
        """Generate map, suspects, clues, and assemble the final scenario.

        Parameters
        ----------
        expansion_result : ScenarioExpansion
            The validated expansion to build content from.
        request_id : str
            Request ID for state persistence.
        clearability_feedback : str
            If non-empty, feedback from a previous clearability failure.
            Injected into suspect/clue generation prompts for targeted fixes.

        Returns
        -------
        ScenarioResult
            Assembled scenario (not yet clearability-validated).
        """
        # 4. Map Skeleton
        map_skeleton, generated = self._load_or_generate(
            request_id, "map_skeleton",
            lambda: self.map_generator.generate_skeleton(expansion_result),
            "MapSkeleton", MapSkeletonSchema,
            generator=self.map_generator,
        )
        logger.info("Map skeleton generated successfully")
        self._sleep_if_generated(generated)

        # 5. Suspects — with optional clearability feedback
        def _generate_suspects():
            suspect_req = SuspectGenerationRequest.from_expansion(
                expansion_result, map_skeleton
            )
            result = self.suspect_generator.generate(
                suspect_req,
                clearability_feedback=clearability_feedback,
            )
            if result is not None:
                inject_sequential_id(result, "fact_id")
            return result

        suspects_result, generated = self._load_or_generate(
            request_id, "suspects_result",
            _generate_suspects,
            "SuspectList", SuspectGenerationListSchema,
            generator=self.suspect_generator,
        )
        logger.info("Suspects generated successfully")
        self._sleep_if_generated(generated)

        # 6. Clues — with optional clearability feedback
        clue_result, generated = self._load_or_generate(
            request_id, "clue_result",
            lambda: self.clue_generator.generate_clues(
                expansion_result, map_skeleton,
                clearability_feedback=clearability_feedback,
            ),
            "ClueSet", ClueSetSchema,
            generator=self.clue_generator,
        )
        logger.info("Clues generated successfully")
        self._sleep_if_generated(generated)

        # 7. Furniture 생성 (skeleton만 필요 — detail보다 먼저)
        furniture_result, generated = self._load_or_generate(
            request_id, "furniture_result",
            lambda: self.map_generator.generate_furniture(
                expansion_result, map_skeleton
            ),
            "Furniture", RoomFurnitureSchema,
            generator=self.map_generator,
        )
        logger.info("Furniture generated successfully")
        self._sleep_if_generated(generated)

        # 8. Map Detail 생성 (가구 위치를 피해 단서·용의자 배치)
        map_result, generated = self._load_or_generate(
            request_id, "map_detail",
            lambda: self.map_generator.generate_detail(
                expansion_result, map_skeleton, clue_result, furniture_result
            ),
            "MapDetail", MapOutputSchema,
            generator=self.map_generator,
        )
        logger.info("Map detail generated successfully")
        self._sleep_if_generated(generated)

        # 9. 최종 결과 조합
        final_scenario = ScenarioResult(
            **expansion_result.model_dump(),
            clues=clue_result.clues,
            map=map_result,
            suspects=[SuspectSchema.from_generation(generation) for generation in suspects_result.suspects],
            furniture=furniture_result.furniture,
        )

        return final_scenario

    def _save_critic_evaluation_history(
        self,
        request_id: str,
        regen_attempt: int,
        result,
    ):
        """Save all critic evaluation iterations to disk with descriptive names.

        File naming: {request_id}_critic_eval_regen{N}_iter{M}.json
        where N = outer regen attempt, M = inner refinement iteration.
        """
        for aggregated in result.evaluation_history:
            step_name = (
                f"critic_eval_regen{regen_attempt}_iter{aggregated.iteration}"
            )
            self.state_manager.save_intermediate_state(
                request_id, step_name, aggregated
            )
        # Save the final refinement decision
        summary = {
            "regen_level": result.regen_level.value,
            "last_feedback": result.last_feedback,
            "total_iterations": len(result.evaluation_history),
        }
        self.state_manager.save_intermediate_state(
            request_id,
            f"critic_decision_regen{regen_attempt}",
            summary,
        )

    def _generate_and_validate_expansion(
        self,
        case_state: str,
        request_id: str,
    ) -> ScenarioExpansion:
        """Generate skeleton & expansion, then run critic loop.

        If critics fail on expansion-level issues, re-generate expansion.
        If critics fail on skeleton-level issues, re-generate from skeleton.
        Retries up to MAX_CRITIC_REGEN times total.

        Parameters
        ----------
        case_state : str
            The narrative case synopsis.
        request_id : str
            Request ID for state persistence.

        Returns
        -------
        ScenarioExpansion
            A critic-approved expansion.
        """
        for regen_attempt in range(MAX_CRITIC_REGEN + 1):
            # 2. Skeleton 생성
            # On regen, clear cached skeleton/expansion so they're regenerated
            if regen_attempt > 0:
                logger.info(
                    f"Critic regen attempt {regen_attempt}/{MAX_CRITIC_REGEN}"
                )
                self.state_manager.clear_intermediate_state(
                    request_id, "skeleton_result"
                )
                self.state_manager.clear_intermediate_state(
                    request_id, "expansion_result"
                )

            skeleton_result, generated = self._load_or_generate(
                request_id, "skeleton_result",
                lambda: self.scenario_generator.generate_skeleton(case_state),
                "ScenarioSkeleton", ScenarioSkeleton,
                generator=self.scenario_generator,
            )
            logger.info("Skeleton generated successfully")
            self._sleep_if_generated(generated)

            # 3. Expansion 생성
            expansion_result, generated = self._load_or_generate(
                request_id, "expansion_result",
                lambda: self.scenario_generator.generate_expansion(skeleton_result),
                "ScenarioExpansion", ScenarioExpansion,
                generator=self.scenario_generator,
            )

            logger.info("Expansion generated successfully")

            # Critic 평가 및 리파인먼트
            logger.info("Starting critic evaluation on expansion...")
            result = self.refiner.evaluate_and_refine(expansion_result)

            # Save critic evaluation history
            self._save_critic_evaluation_history(
                request_id, regen_attempt, result
            )

            if result.regen_level == RegenLevel.NONE:
                # All critics passed — save approved expansion and return
                logger.info("Expansion passed all critic evaluations.")
                self.state_manager.save_intermediate_state(
                    request_id, "expansion_result", result.expansion
                )
                return result.expansion

            if result.regen_level == RegenLevel.SKELETON:
                # Need to regenerate from skeleton
                logger.warning(
                    f"Critics require skeleton regen: {result.last_feedback[:200]}..."
                )
                if regen_attempt >= MAX_CRITIC_REGEN:
                    break
                # Clear skeleton too so it's regenerated on next loop
                continue

            if result.regen_level == RegenLevel.EXPANSION:
                # Need to regenerate expansion only
                logger.warning(
                    f"Critics require expansion regen: {result.last_feedback[:200]}..."
                )
                if regen_attempt >= MAX_CRITIC_REGEN:
                    break
                # Clear only expansion
                self.state_manager.clear_intermediate_state(
                    request_id, "expansion_result"
                )
                continue

        # Exhausted all regen attempts — use last expansion as fallback
        logger.error(
            "Critic validation failed after all regen attempts. "
            "Using last generated expansion as fallback."
        )
        return expansion_result

    async def save_to_db(self, scenario: ScenarioResult, db=None) -> int:
        """
        Save generated scenario to database and index for RAG.

        Parameters
        ----------
        scenario : ScenarioResult
            The complete scenario result object
        db : AsyncSession, optional
            Database session for RAG indexing. If not provided, only saves scenario.

        Returns
        -------
        int
            The created scenario ID
        """
        # Save to database
        scenario_id = await self.repository.save_scenario(scenario)
        logger.info(f"Scenario saved to DB with ID: {scenario_id}")

        # Index for RAG if db session provided
        if db is not None:
            try:
                stats = await self.rag_service.index_scenario(db, scenario_id)
                logger.info(f"RAG indexing completed: {stats}")
            except Exception as e:
                logger.warning(f"RAG indexing failed (scenario still saved): {e}")

        return scenario_id

    async def generate_and_save(
        self,
        pre_input: str,
        request_id: str = None,
        db=None
    ) -> tuple[ScenarioResult, int]:
        """
        Generate scenario and save to database with RAG indexing.

        Parameters
        ----------
        pre_input : str
            Input for scenario generation
        request_id : str, optional
            Unique identifier for the generation request.
        db : AsyncSession, optional
            Database session for RAG indexing

        Returns
        -------
        tuple[ScenarioResult, int]
            Tuple of (scenario_result, scenario_id)
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        # Generate scenario (sync operation)
        scenario_result = await asyncio.to_thread(
            self.generate,
            pre_input,
            request_id
        )

        # Save to DB and index for RAG
        scenario_id = await self.save_to_db(scenario_result, db)

        return scenario_result, scenario_id
