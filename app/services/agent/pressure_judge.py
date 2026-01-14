import json
from typing import Optional

from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.pressure import PressureJudgeOutput


class PressureJudge:
    """
    유저 입력을 분석하여 pressure 변화량을 판단하는 Judge LLM.
    SuspectActor와 분리되어 독립적으로 평가.

    핵심 원칙: 논리적 압박만 효과가 있음. 빈 협박은 역효과.
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load("app/prompts/judge/system.txt")

    def evaluate(
        self,
        user_message: str,
        suspect_summary: str,
        current_pressure: int,
        conversation_context: str,
        evidence_presented: Optional[dict] = None,
        suspect_alibi: Optional[str] = None,
        suspect_timeline: Optional[str] = None
    ) -> PressureJudgeOutput:
        """
        유저의 질문/행동을 평가하여 pressure 변화량 반환.

        Args:
            user_message: 유저가 보낸 메시지
            suspect_summary: 용의자 요약 정보 (이름, 역할, 범인여부)
            current_pressure: 현재 pressure (0-100)
            conversation_context: 최근 대화 맥락
            evidence_presented: 제시된 증거 (있다면)
            suspect_alibi: 용의자의 알리바이 요약
            suspect_timeline: 용의자의 타임라인 요약

        Returns:
            PressureJudgeOutput: pressure_delta, reasoning, detected_strategy, is_critical_hit
        """

        input_data = {
            "user_message": user_message,
            "evidence_presented": evidence_presented,
            "current_pressure": current_pressure,
            "suspect_summary": suspect_summary,
            "suspect_alibi": suspect_alibi or "정보 없음",
            "suspect_timeline": suspect_timeline or "정보 없음",
            "conversation_context": conversation_context
        }

        raw = self.llm.complete(
            system=self.system_prompt,
            user=json.dumps(input_data, ensure_ascii=False),
            response_schema=PressureJudgeOutput.model_json_schema()
        )

        json_text = extract_json(raw)
        data = safe_json_load(json_text)

        return PressureJudgeOutput.model_validate(data)
