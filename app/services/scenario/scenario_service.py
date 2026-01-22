import time
import logging

from pydantic import ValidationError

from app.models.schemas import ClueSetSchema
from app.models.schemas.scenario import ScenarioSkeleton, ScenarioExpansion, ScenarioResult
from app.models.schemas.map import MapOutputSchema, MapSkeletonSchema
from app.models.schemas.suspect import SuspectGenerationRequest, SuspectListSchema
from app.services.agent.clue_generator import ClueGenerator
from app.services.agent.map_generator import MapGenerator
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.scenario_generator import ScenarioGenerator
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.llm.llm_client import LLMClient
from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.rag import get_rag_service


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

    def generate(self,
                 pre_input: str,
                 scenario_id: int) -> dict:
        # 생성 시작
        # 평서문 생성
        case_state = self.scenario_generator.generate_case(pre_input)

        # 요청 속도 조절
        time.sleep(3)

        # 1차로 스켈레톤 생성
        skeleton_result: ScenarioSkeleton | None = None
        for attempt in range(3):
            try:
                skeleton_result = self.scenario_generator.generate_skeleton(case_state)
                break
            except ValidationError as error:
                print(error)

        if skeleton_result is None:
            raise RuntimeError("Skeleton of Scenario failed to generate")

        print("Skeleton generated successfully")
        # 2차로 디테일 생성
        time.sleep(3)

        expansion_result: ScenarioExpansion | None = None
        for attempt in range(3):
            try:
                expansion_result = self.scenario_generator.generate_expansion(skeleton_result)
                break
            except ValidationError as error:
                print(error)

        if expansion_result is None:
            raise RuntimeError("Expansion of Scenario failed to generate")

        print("Expansion generated successfully")
        time.sleep(3)

        # 3차 맵 스켈레톤 생성 (방 구조 + 복도)
        print("Map skeleton generating...")
        map_skeleton: MapSkeletonSchema | None = None
        for attempt in range(3):
            try:
                map_skeleton = self.map_generator.generate_skeleton(expansion_result)
                break
            except ValidationError as error:
                print(error)
                time.sleep(2)

        if map_skeleton is None:
            raise RuntimeError("Map skeleton failed to generate")

        print("Map skeleton generated successfully")
        time.sleep(3)

        # 4차 단서 생성 (map_skeleton 정보 포함)
        print("Clues generating...")
        clue_result: ClueSetSchema | None = None

        for attempt in range(3):
            try:
                clue_result = self.clue_generator.generate_clues(expansion_result, map_skeleton)
                break
            except ValidationError as error:
                print(error)
                time.sleep(2)

        if clue_result is None:
            raise RuntimeError("Clue of Scenario failed to generate")

        print("Clues generated successfully")
        time.sleep(3)

        # 5차 용의자 생성 (clue + map_skeleton 정보 포함)
        print("Suspects generating...")
        suspects_result: SuspectListSchema | None = None
        suspect_req = SuspectGenerationRequest.from_expansion(
            expansion_result, clue_result.clues, map_skeleton
        )

        for attempt in range(3):
            try:
                suspects_result = self.suspect_generator.generate(suspect_req)
                break
            except Exception as error:
                print(f"Suspect generation error: {error}")
                time.sleep(2)

        if suspects_result is None:
            raise RuntimeError("Suspects of Scenario failed to generate")

        print("Suspects generated successfully")
        time.sleep(3)

        # 6차 맵 디테일 생성 (skeleton + clue 기반)
        print("Map detail generating...")
        map_result: MapOutputSchema | None = None
        for attempt in range(3):
            try:
                map_result = self.map_generator.generate_detail(
                    expansion_result, map_skeleton, clue_result
                )
                break
            except ValidationError as error:
                print(error)
                time.sleep(2)

        if map_result is None:
            raise RuntimeError("Map detail failed to generate")

        print("Map detail generated successfully")

        # Combine into ScenarioResult
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
        scenario_data = self.generate(pre_input, scenario_id=0)

        # Save to DB and index for RAG
        scenario_id = await self.save_to_db(scenario_data, db)

        return scenario_data, scenario_id
