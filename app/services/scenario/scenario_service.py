import time
import asyncio
import logging

from app.models.schemas.clue import ClueGenerationRequest
from app.models.schemas.scenario import ScenarioResult
from app.models.schemas.suspect import SuspectGenerationRequest
from app.services.agent.clue_generator import ClueGenerator
from app.services.agent.map_generator import MapGenerator
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.scenario_generator import ScenarioGenerator
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.llm.llm_client import LLMClient
from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.rag import get_rag_service
from app.core.json_retry import JSONParseRetry
from app.services.scenario.scenario_generate_helper import inject_sequential_id, find_facts

logger = logging.getLogger(__name__)


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
        self.repository = ScenarioRepository()
        self.rag_service = get_rag_service()

        # JSON 재시도 정책
        self.json_retry = JSONParseRetry(
            max_attempts=3,
            backoff_seconds=2.0,
            backoff_multiplier=1.5  # 2초 → 3초 → 4.5초
        )

    def generate(self,
                 pre_input: str) -> dict:
        # 생성 시작
        # 1. 평서문 생성
        case_state = self.scenario_generator.generate_case(pre_input)

        # 요청 속도 조절
        time.sleep(3)

        # 2. Skeleton 생성 (재시도 적용)
        skeleton_result = self.json_retry.parse_with_retry(
            parser_func=lambda: self.scenario_generator.generate_skeleton(case_state),
            schema_name="ScenarioSkeleton"
        )

        if skeleton_result is None:
            raise RuntimeError("Skeleton generation failed after retries")

        logger.info("Skeleton generated successfully")
        time.sleep(3)

        # 3. Expansion 생성 (재시도 적용)
        expansion_result = self.json_retry.parse_with_retry(
            parser_func=lambda: self.scenario_generator.generate_expansion(skeleton_result),
            schema_name="ScenarioExpansion"
        )

        if expansion_result is None:
            raise RuntimeError("Expansion generation failed after retries")

        logger.info("Expansion generated successfully")
        time.sleep(3)

        # 4. Map Skeleton 생성 (재시도 적용)
        map_skeleton = self.json_retry.parse_with_retry(
            parser_func=lambda: self.map_generator.generate_skeleton(expansion_result),
            schema_name="MapSkeleton"
        )

        if map_skeleton is None:
            raise RuntimeError("Map skeleton generation failed after retries")

        logger.info("Map skeleton generated successfully")
        time.sleep(3)

        # 5. Suspects 생성 (재시도 적용)
        suspect_req = SuspectGenerationRequest.from_expansion(
            expansion_result, map_skeleton
        )

        suspects_result = self.json_retry.parse_with_retry(
            parser_func=lambda: self.suspect_generator.generate(suspect_req),
            schema_name="SuspectList"
        )

        if suspects_result is None:
            raise RuntimeError("Suspect generation failed after retries")

        inject_sequential_id(suspects_result, "fact_id")

        logger.info("Suspects generated successfully")
        time.sleep(3)

        # 6. Clues 생성 (재시도 적용)
        clue_result = ClueGenerationRequest.from_expansion(
            expansion_result, find_facts(suspects_result)
        )

        clue_result = self.json_retry.parse_with_retry(
            parser_func=lambda: self.clue_generator.generate_clues(expansion_result, map_skeleton),
            schema_name="ClueSet"
        )

        if clue_result is None:
            raise RuntimeError("Clue generation failed after retries")

        logger.info("Clues generated successfully")
        time.sleep(3)

        # 7. Map Detail 생성 (재시도 적용)
        map_result = self.json_retry.parse_with_retry(
            parser_func=lambda: self.map_generator.generate_detail(
                expansion_result, map_skeleton, clue_result
            ),
            schema_name="MapDetail"
        )

        if map_result is None:
            raise RuntimeError("Map detail generation failed after retries")

        logger.info("Map detail generated successfully")

        # 8. 최종 결과 조합
        final_scenario = ScenarioResult(
            **expansion_result.model_dump(),  # 본인
            clues=clue_result,  # 추가
            map=map_result,  # 추가
            suspects=suspects_result.suspects  # 추가
        )

        return final_scenario.model_dump(mode='json')

    async def save_to_db(self, scenario_data: dict, db=None) -> int:
        """
        Save generated scenario to database and index for RAG.

        Parameters
        ----------
        scenario_data : dict
            The scenario data from generate() method
        db : AsyncSession, optional
            Database session for RAG indexing. If not provided, only saves scenario.

        Returns
        -------
        int
            The created scenario ID
        """
        # Save to database
        scenario_id = await self.repository.save_scenario(scenario_data)
        logger.info(f"Scenario saved to DB with ID: {scenario_id}")

        # Index for RAG if db session provided
        if db is not None:
            try:
                stats = await self.rag_service.index_scenario(db, scenario_id)
                logger.info(f"RAG indexing completed: {stats}")
            except Exception as e:
                logger.warning(f"RAG indexing failed (scenario still saved): {e}")

        return scenario_id

    async def generate_and_save(self, pre_input: str, db=None) -> tuple[dict, int]:
        """
        Generate scenario and save to database with RAG indexing.

        Parameters
        ----------
        pre_input : str
            Input for scenario generation
        db : AsyncSession, optional
            Database session for RAG indexing

        Returns
        -------
        tuple[dict, int]
            Tuple of (scenario_data, scenario_id)
        """
        # Generate scenario (sync operation)

        scenario_data = await asyncio.to_thread(
            self.generate,
            pre_input,
        )

        # Save to DB and index for RAG
        scenario_id = await self.save_to_db(scenario_data, db)

        return scenario_data, scenario_id
