'''
suspect_service.py

용의자에 대한 정보를 얻어 해당 AI를 구성하는 놈입니다.
JSON dict를 직접 조작하지 않습니다.

'''

from app.models.schemas import SuspectGenerationRequest
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.llm.gemini_client import GeminiClient


class SuspectService:
    """
    SuspectService는 '용의자 생성 파이프라인'의 조립자 역할만 수행한다.
    판단, 검증, 생성은 각각의 책임 주체에게 위임한다.
    """

    def __init__(self):
        llm_client = GeminiClient()
        self.agent = SuspectGenerator(llm_client)
        self.validator = ConsistencyValidator()

    def generate(self, pre_json: dict) -> dict:
        """
        선 JSON(pre_json)을 입력으로 받아
        - 유효성 검증
        - 생성 가능성 검증
        - Agent 호출
        후 JSON을 반환한다.
        :param pre_json: Generate from Scenario LLM
        :return: Post JSON dict
        """

        request = SuspectGenerationRequest.model_validate(pre_json)

        result = self.validator.validate_pre_json(request=request)
        if not result.is_valid:
            errors = [i.message for i in result.issues]
            raise ValueError(f"Pre-validation failed: {errors}")

        agent_input = self._build_agent_input(request)

        last_issues = None

        for _ in range(3):
            post_json = self.agent.generate(agent_input)
            post_result = self.validator.validate_post_json(post_json)

            if post_result.is_valid:
                return post_json

            last_issues = post_result.issues

        raise RuntimeError(
            f"Failed to generate valid suspects. "
            f"Last issues: {[i.code for i in last_issues]}"
        )

    def _build_agent_input(self, request: SuspectGenerationRequest) -> dict:
        return {
            "case_context": request.case_context.model_dump(mode="json"),
            "world_context": request.world_context.model_dump(mode="json"),
            "ground_truth": request.ground_truth.model_dump(mode="json"),
            "generation_config": request.generation_config.model_dump(mode="json"),
            "constraints": (
                request.constraints.model_dump(mode="json")
                if request.constraints else None
            )
        }
