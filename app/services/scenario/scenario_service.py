from pydantic import ValidationError

from app.models.schemas.scenario import ScenarioSkeleton, ScenarioExpansion
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.scenario_agent import ScenarioAgent
from app.services.llm.gemini_client import GeminiClient
import time


class ScenarioService:

    def __init__(self):
        llm_client = GeminiClient() # TODO : 여기서 LLM CLIENT 수정
        self.agent = ScenarioAgent(llm_client)
        self.validator = ConsistencyValidator()

    def generate(self, pre_input: str) -> dict:
        # 생성 시작
        # 평서문 생성
        case_state = self.agent.generate_case(pre_input)

        # TODO : 테스트 코드
        print(case_state)

        # 요청 속도 조절
        time.sleep(3)

        # 1차로 스켈레톤 생성
        skeleton_result: ScenarioSkeleton | None = None
        for attempt in range(3):
            try:
                skeleton_result = self.agent.generate_skeleton(case_state)
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
                expansion_result = self.agent.generate_expansion(skeleton_result)
                break
            except ValidationError as error:
                print(error)

        if expansion_result is None:
            raise RuntimeError("Expansion of Scenario failed to generate")

        return expansion_result.model_dump()
