from pydantic import ValidationError

from app.models.schemas import ClueSetSchema
from app.models.schemas.scenario import ScenarioSkeleton, ScenarioExpansion, ScenarioResult
from app.models.schemas.map import MapOutputSchema
from app.models.schemas.suspect import SuspectGenerationRequest, SuspectListSchema
from app.services.agent.clue_generator import ClueGenerator
from app.services.agent.map_generator import MapGenerator
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.scenario_generator import ScenarioGenerator
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.llm.gemini_client import GeminiClient
import time


class ScenarioService:

    def __init__(self):
        llm_client = GeminiClient() # TODO : 여기서 LLM CLIENT 수정
        self.scenario_generator = ScenarioGenerator(llm_client)
        self.clue_generator = ClueGenerator(llm_client)
        self.map_generator = MapGenerator(llm_client)
        self.suspect_generator = SuspectGenerator(llm_client)
        self.validator = ConsistencyValidator()

    def generate(self, pre_input: str) -> dict:
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

        # 2차 단서 생성 (suspect보다 먼저 생성해야 trigger_evidence_ids 설정 가능)
        print("Clues generating...")
        clue_result: ClueSetSchema | None = None

        for attempt in range(3):
            try:
                clue_result = self.clue_generator.generate_clues(expansion_result)
                break
            except ValidationError as error:
                print(error)
                time.sleep(2)

        if clue_result is None:
            raise RuntimeError("Clue of Scenario failed to generate")

        print("Clues generated successfully")
        time.sleep(3)

        # 3차 용의자 생성 (clue 정보를 포함하여 생성)
        print("Suspects generating...")
        suspects_result: SuspectListSchema | None = None
        suspect_req = SuspectGenerationRequest.from_expansion(expansion_result, clue_result.clues)

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

        # 4차 맵 생성
        map_result: MapOutputSchema | None = None
        for attempt in range(3):
            try:
                map_result = self.map_generator.generate_map(expansion_result, clue_result)
                break
            except ValidationError as error:
                print(error)

        if map_result is None:
             raise RuntimeError("Map of Scenario failed to generate")

        # Combine into ScenarioResult
        final_scenario = ScenarioResult(
            **expansion_result.model_dump(), # 본인
            clues=clue_result, # 추가
            map=map_result, # 추가
            suspects=suspects_result.suspects # 추가
        )

        return final_scenario.model_dump(mode='json')
