"""Solve Validator for evaluating user's reasoning against ground truth."""
import json

from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.solve import SolveValidationResult


class SolveValidator:
    """
    유저의 추리를 ground truth와 비교하여 점수를 매기는 LLM Judge.
    PressureJudge 패턴을 참고하여 구현.

    평가 요소 (각 20점):
    - 범인: 범인을 정확히 지목했는지
    - 동기: 범행 동기를 파악했는지
    - 수법: 범행 방법을 설명했는지
    - 시간: 범행 시간을 파악했는지
    - 장소: 범행 장소를 파악했는지
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load("app/prompts/solve/system.txt")

    def validate(
        self,
        ground_truth: str,
        user_solution: str
    ) -> SolveValidationResult:
        """
        유저의 추리를 ground truth와 비교하여 점수 산출.

        Parameters
        ----------
        ground_truth : str
            정답 요약 (범인명, 동기, 수법, 시간, 장소 포함)
        user_solution : str
            유저가 제출한 추리 내용

        Returns
        -------
        SolveValidationResult
            각 요소별 점수 및 피드백
        """
        input_data = {
            "ground_truth": ground_truth,
            "user_solution": user_solution
        }

        raw = self.llm.complete(
            system=self.system_prompt,
            user=json.dumps(input_data, ensure_ascii=False),
            response_schema=SolveValidationResult.model_json_schema()
        )

        json_text = extract_json(raw)
        data = safe_json_load(json_text)

        return SolveValidationResult.model_validate(data)
