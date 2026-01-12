from pydantic import ValidationError

from app.models.schemas import ClueSetSchema
from app.models.schemas.scenario import ScenarioSkeleton, ScenarioExpansion, ScenarioResult
from app.models.schemas.map import MapOutputSchema
from app.services.agent.clue_generator import ClueGenerator
from app.services.agent.map_generator import MapGenerator
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.scenario_generator import ScenarioGenerator
from app.services.llm.gemini_client import GeminiClient
import time


class ScenarioService:

    def __init__(self):
        llm_client = GeminiClient() # TODO : 여기서 LLM CLIENT 수정
        self.scenario_generator = ScenarioGenerator(llm_client)
        self.clue_generator = ClueGenerator(llm_client)
        self.map_generator = MapGenerator(llm_client)
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

        # 3차 단서 생성
        clue_result: ClueSetSchema | None = None

        for attempt in range(3):
            try:
                clue_result = self.clue_generator.generate_clues(expansion_result)
                break
            except ValidationError as error:
                print(error)

        if clue_result is None:
            raise RuntimeError("Clue of Scenario failed to generate")

        # # 4차 맵 생성
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
            map=map_result # 추가
        )

        return final_scenario.model_dump(mode='json')
