import json
from typing import List, Optional

from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.suspect import SuspectSchema
from app.models.domain.suspect_state import SuspectState


class SuspectActor:
    """
    용의자를 연기하며 대화를 생성하는 Actor LLM.
    현재 pressure와 공개된 비밀을 기반으로 응답 생성.
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt_template = PromptLoader.load("app/prompts/actor/system.txt")

    def generate_response(
        self,
        suspect: SuspectSchema,
        state: SuspectState,
        user_message: str,
        evidence_presented: Optional[dict] = None
    ) -> str:
        """
        용의자 응답 생성.

        Args:
            suspect: 용의자 스키마 데이터
            state: 현재 런타임 상태 (pressure, revealed secrets 등)
            user_message: 유저 메시지
            evidence_presented: 제시된 증거 (있다면)

        Returns:
            용의자의 응답 문자열
        """

        # 1. 현재 pressure에서 공개 가능한 비밀 계산
        revealed_secrets = self._get_revealed_secrets(suspect, state)

        # 2. 프롬프트 데이터 구성
        prompt_data = {
            "name": suspect.name,
            "role": suspect.role,
            "age": suspect.age,
            "gender": suspect.gender,
            "description": suspect.description,
            "speech_style": suspect.personality.speech_style,
            "emotional_tendency": suspect.personality.emotional_tendency,
            "lying_pattern": suspect.personality.lying_pattern,
            "alibi_summary": suspect.alibi_summary,
            "timeline_summary": self._format_timeline(suspect.timeline),
            "pressure_tier": state.get_pressure_tier(),
            "pressure_level": state.current_pressure,
            "is_culprit": suspect.is_culprit,
            "revealed_secrets": self._format_secrets(revealed_secrets),
            "evidence_presented": json.dumps(evidence_presented, ensure_ascii=False) if evidence_presented else "None",
            "chat_history": self._format_history(state.get_recent_history(10)),
        }

        # 3. 시스템 프롬프트 포맷팅
        formatted_prompt = self.system_prompt_template.format(**prompt_data)

        # 4. LLM 호출
        response = self.llm.complete(
            system=formatted_prompt,
            user=user_message
        )

        return response

    def _get_revealed_secrets(
        self,
        suspect: SuspectSchema,
        state: SuspectState
    ) -> List[str]:
        """현재 pressure에서 공개 가능한 비밀 목록"""
        revealed = []
        for secret in suspect.secrets:
            # threshold 이하이거나 trigger 증거가 제시된 경우
            if secret.threshold <= state.current_pressure:
                revealed.append(secret.content)
            elif any(eid in state.evidence_seen_ids for eid in secret.trigger_evidence_ids):
                revealed.append(secret.content)
        return revealed

    def _format_timeline(self, timeline: list) -> str:
        """타임라인을 문자열로 포맷"""
        lines = []
        for entry in timeline:
            prove_str = "(증명가능)" if entry.can_prove else "(미확인)"
            witness_str = f" - 증인: {entry.witness}" if entry.witness else ""
            lines.append(f"- {entry.time}: {entry.location}에서 {entry.activity} {prove_str}{witness_str}")
        return "\n".join(lines)

    def _format_secrets(self, secrets: List[str]) -> str:
        """비밀 목록을 문자열로 포맷"""
        if not secrets:
            return "- 공개할 비밀 없음"
        return "\n".join([f"- {s}" for s in secrets])

    def _format_history(self, history: list) -> str:
        """대화 히스토리 포맷"""
        if not history:
            return "(대화 시작)"
        return "\n".join([f"{h['role']}: {h['content']}" for h in history])
