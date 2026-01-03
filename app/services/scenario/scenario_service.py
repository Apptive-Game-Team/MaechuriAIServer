from pydantic import ValidationError

from app.models.schemas.scenario import ScenarioSkeleton, ScenarioExpansion
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.scenario_agent import ScenarioAgent
from app.services.llm.gemini_client import GeminiClient


class ScenarioService:

    def __init__(self):
        llm_client = GeminiClient() # TODO : 여기서 LLM CLIENT 수정
        self.agent = ScenarioAgent(llm_client)
        self.validator = ConsistencyValidator()

    def generate(self, pre_input: str) -> dict:

        # TODO : 현재는 평서문으로 초기 설정을 받는다. 이후 고도화 단계에서 형식을 지정해주는 게 좋을 듯.
        # 입력값 확인 시작
        # result = self.validator.validate_pre_json(pre_input)
        # if not result.is_valid:
        #     errors = [i.message for i in result.issues]
        #     raise ValueError(f"Pre-validation failed: {errors}")

        # 생성 시작
        # 1차로 스켈레톤 생성
        skeleton_result: ScenarioSkeleton | None = None
        for attempt in range(3):
            try:
                skeleton_result = self.agent.generate_skeleton(pre_input)
                break
            except ValidationError as error:
                print(error)

        if skeleton_result is None:
            raise RuntimeError("Skeleton of Scenario failed to generate")

        # TODO : TEST CODE
        print(skeleton_result.model_dump())

        # 2차로 디테일 생성

        expansion_result: ScenarioExpansion | None = None
        for attempt in range(3):
            try:
                expansion_result = self.agent.generate_expansion(skeleton_result)
                break
            except ValidationError as error:
                print(error)

        if expansion_result is None:
            raise RuntimeError("Expansion of Scenario failed to generate")

        # TODO : TEST CODE
        print(skeleton_result.model_dump())

        return expansion_result.model_dump()
