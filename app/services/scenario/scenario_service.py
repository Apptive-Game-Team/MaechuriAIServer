import time
import asyncio
import logging
import uuid

from app.models.schemas.scenario import ScenarioResult, ScenarioExpansion
from app.models.schemas.suspect import SuspectSchema
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
from app.services.scenario.scenario_state_manager import ScenarioStateManager
from app.services.scenario.pipeline import (
    PipelineRunner,
    CaseGenerationStep,
    SkeletonGenerationStep,
    ExpansionGenerationStep,
    MapSkeletonStep,
    SuspectGenerationStep,
    ClueGenerationStep,
    FurnitureGenerationStep,
    MapDetailStep,
)


logger = logging.getLogger(__name__)

# Max times we'll regenerate skeleton/expansion due to critic failures
MAX_CRITIC_REGEN = 2
# Max times we'll regenerate the full scenario due to clearability failures
MAX_CLEARABILITY_REGEN = 2


class ScenarioService:
    """Orchestrates the full scenario generation pipeline.

    The generation is split into two declarative pipelines:

    Narrative pipeline
        ``theme`` → ``case_state`` → ``skeleton`` → ``expansion``

        Each step is an independent :class:`PipelineStep` that declares
        its inputs and output.  The :class:`PipelineRunner` auto-schedules
        execution in topological order.  After the expansion is produced it
        is validated by a critic loop that may request regeneration.

    Content pipeline
        ``expansion`` → ``map_skeleton`` / ``suspects`` / ``clues`` /
        ``furniture`` → ``map_detail``

        Suspects and clues also accept ``clearability_feedback`` so they
        can be refined when the clearability evaluator rejects the first
        attempt.

    Both pipelines cache every intermediate result to disk via
    :class:`ScenarioStateManager`, enabling crash recovery and
    incremental regeneration.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialise ScenarioService with all required sub-agents.

        Parameters
        ----------
        llm_client : LLMClient
            LLM client instance (e.g. GeminiClient).
        """
        scenario_generator = ScenarioGenerator(llm_client)
        clue_generator = ClueGenerator(llm_client)
        map_generator = MapGenerator(llm_client)
        suspect_generator = SuspectGenerator(llm_client)

        self.validator = ConsistencyValidator()
        self.refiner = ScenarioRefiner(llm_client)
        self.clearability_evaluator = ClearabilityEvaluator(llm_client)
        self.repository = ScenarioRepository()
        self.rag_service = get_rag_service()
        self.state_manager = ScenarioStateManager()

        # Shared JSON retry policy (token escalation on each attempt)
        json_retry = JSONParseRetry(
            max_attempts=3,
            backoff_seconds=2.0,
            backoff_multiplier=1.5,
        )

        # ── Narrative pipeline ──────────────────────────────────────────
        # theme → case_state → skeleton → expansion
        self._narrative_pipeline = PipelineRunner(
            steps=[
                CaseGenerationStep(scenario_generator),
                SkeletonGenerationStep(scenario_generator),
                ExpansionGenerationStep(scenario_generator),
            ],
            state_manager=self.state_manager,
            json_retry=json_retry,
        )

        # ── Content pipeline ────────────────────────────────────────────
        # expansion + clearability_feedback →
        #   map_skeleton / suspects / clues / furniture → map_detail
        self._content_pipeline = PipelineRunner(
            steps=[
                MapSkeletonStep(map_generator),
                SuspectGenerationStep(suspect_generator),
                ClueGenerationStep(clue_generator),
                FurnitureGenerationStep(map_generator),
                MapDetailStep(map_generator),
            ],
            state_manager=self.state_manager,
            json_retry=json_retry,
        )

    def generate(self, pre_input: str, request_id: str = None) -> ScenarioResult:
        """Generate a complete, critic- and clearability-validated scenario.

        Parameters
        ----------
        pre_input : str
            Theme or seed text for the mystery case.
        request_id : str, optional
            Unique run identifier for intermediate caching.  A UUID is
            generated when not supplied.

        Returns
        -------
        ScenarioResult
            Fully assembled scenario ready for database persistence.
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        # Phase 1: narrative pipeline + critic loop
        expansion_result = self._generate_and_validate_expansion(
            pre_input, request_id
        )

        # Phase 2: content pipeline + clearability loop
        return self._generate_content_with_clearability_check(
            expansion_result, request_id
        )

    # ------------------------------------------------------------------
    # Phase 1: narrative pipeline with critic retry loop
    # ------------------------------------------------------------------

    def _generate_and_validate_expansion(
        self,
        theme: str,
        request_id: str,
    ) -> ScenarioExpansion:
        """Run the narrative pipeline and validate the expansion with critics.

        Retries up to ``MAX_CRITIC_REGEN`` times, clearing cached skeleton
        or expansion as directed by the critic feedback.

        Parameters
        ----------
        theme : str
            Theme / seed text passed to :class:`CaseGenerationStep`.
        request_id : str
            Used for intermediate state caching.

        Returns
        -------
        ScenarioExpansion
            A critic-approved expansion (or the last generated one as a
            fallback when all retries are exhausted).
        """
        expansion_result = None

        for regen_attempt in range(MAX_CRITIC_REGEN + 1):
            if regen_attempt > 0:
                logger.info(
                    "Critic regen attempt %d/%d", regen_attempt, MAX_CRITIC_REGEN
                )

            state = self._narrative_pipeline.run(
                initial_state={"theme": theme},
                request_id=request_id,
            )
            expansion_result = state["expansion"]

            logger.info("Starting critic evaluation on expansion...")
            result = self.refiner.evaluate_and_refine(expansion_result)
            self._save_critic_evaluation_history(request_id, regen_attempt, result)

            if result.regen_level == RegenLevel.NONE:
                logger.info("Expansion passed all critic evaluations.")
                self.state_manager.save_intermediate_state(
                    request_id, "expansion", result.expansion
                )
                return result.expansion

            if result.regen_level == RegenLevel.SKELETON:
                logger.warning(
                    "Critics require skeleton regen: %s...",
                    result.last_feedback[:200],
                )
                if regen_attempt >= MAX_CRITIC_REGEN:
                    break
                self._narrative_pipeline.clear(
                    request_id, "skeleton", "expansion"
                )
                continue

            if result.regen_level == RegenLevel.EXPANSION:
                logger.warning(
                    "Critics require expansion regen: %s...",
                    result.last_feedback[:200],
                )
                if regen_attempt >= MAX_CRITIC_REGEN:
                    break
                self._narrative_pipeline.clear(request_id, "expansion")
                continue

        logger.error(
            "Critic validation failed after all regen attempts. "
            "Using last generated expansion as fallback."
        )
        return expansion_result

    # ------------------------------------------------------------------
    # Phase 2: content pipeline with clearability retry loop
    # ------------------------------------------------------------------

    def _generate_content_with_clearability_check(
        self,
        expansion_result: ScenarioExpansion,
        request_id: str,
    ) -> ScenarioResult:
        """Run the content pipeline and validate clearability.

        On failure the suspects and clues are regenerated with targeted
        feedback from the clearability evaluator, keeping the map skeleton
        and detail intact.

        Parameters
        ----------
        expansion_result : ScenarioExpansion
            The critic-approved expansion.
        request_id : str
            Used for intermediate state caching.

        Returns
        -------
        ScenarioResult
            A clearability-validated, fully assembled scenario.

        Raises
        ------
        RuntimeError
            If the scenario fails clearability after all retry attempts.
        """
        clearability_feedback: str = ""
        evaluation = None

        for attempt in range(MAX_CLEARABILITY_REGEN + 1):
            if attempt > 0:
                logger.info(
                    "Clearability regen attempt %d/%d — regenerating suspects + clues",
                    attempt,
                    MAX_CLEARABILITY_REGEN,
                )
                self._content_pipeline.clear(
                    request_id, "suspects", "clues"
                )

            state = self._content_pipeline.run(
                initial_state={
                    "expansion": expansion_result,
                    "clearability_feedback": clearability_feedback,
                },
                request_id=request_id,
            )

            final_scenario = ScenarioResult(
                **expansion_result.model_dump(),
                clues=state["clues"].clues,
                map=state["map_detail"],
                suspects=[
                    SuspectSchema.from_generation(g)
                    for g in state["suspects"].suspects
                ],
                furniture=state["furniture"].furniture,
            )

            logger.info("Starting clearability evaluation...")
            scenario_data = final_scenario.model_dump(mode="json")
            evaluation = self.clearability_evaluator.evaluate(scenario_data)
            self.state_manager.save_intermediate_state(
                request_id,
                f"clearability_eval_attempt{attempt}",
                evaluation,
            )

            if evaluation.is_clearable:
                logger.info("Scenario passed clearability check.")
                return final_scenario

            logger.warning(
                "Scenario failed clearability check: %s",
                evaluation.reason[:300],
            )
            if attempt >= MAX_CLEARABILITY_REGEN:
                break

            clearability_feedback = evaluation.reason
            time.sleep(3)

        raise RuntimeError(
            f"Scenario is not clearable after {MAX_CLEARABILITY_REGEN + 1} attempts. "
            f"Last reason: {evaluation.reason}"
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _save_critic_evaluation_history(
        self,
        request_id: str,
        regen_attempt: int,
        result,
    ) -> None:
        """Persist every critic iteration and the final decision to disk."""
        for aggregated in result.evaluation_history:
            step_name = (
                f"critic_eval_regen{regen_attempt}_iter{aggregated.iteration}"
            )
            self.state_manager.save_intermediate_state(
                request_id, step_name, aggregated
            )
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
