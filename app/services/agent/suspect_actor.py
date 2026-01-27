import json
from typing import List, Optional

from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.suspect import SuspectSchema, FactSchema
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
        clue_presented: Optional[dict] = None,
        rag_context: Optional[str] = None
    ) -> str:
        """
        용의자 응답 생성.

        Args:
            suspect: 용의자 스키마 데이터
            state: 현재 런타임 상태 (pressure, revealed secrets 등)
            user_message: 유저 메시지
            clue_presented: 제시된 단서 (있다면)
            rag_context: RAG로 검색된 관련 컨텍스트 (있다면)

        Returns:
            용의자의 응답 문자열
        """

        # 1. 현재 pressure에서 공개 가능한 비밀 계산
        # rag_context와 중복되는 내용이기에 일단 빼고
        # revealed_facts = self._get_revealed_facts(suspect, state)

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
            "pressure_tier": state.get_pressure_tier(),
            "pressure_level": state.current_pressure,
            "is_culprit": suspect.is_culprit,
            # "revealed_facts": self._format_facts(revealed_facts),
            "clue_presented": json.dumps(clue_presented, ensure_ascii=False) if clue_presented else "None",
            "chat_history": self._format_history(state.get_recent_history(10)),
            "rag_context": rag_context or "",
        }

        # 3. 시스템 프롬프트 포맷팅
        formatted_prompt = self.system_prompt_template.format(**prompt_data)

        # 4. LLM 호출
        response = self.llm.complete(
            system=formatted_prompt,
            user=user_message
        )

        return response

    # def _get_revealed_facts(
    #     self,
    #     suspect: SuspectSchema,
    #     state: SuspectState
    # ) -> List[FactSchema]:
    #     """현재 pressure에서 공개 가능한 비밀 목록"""
    #     revealed = []
    #     for fact in suspect.facts:
    #         # threshold 이하이거나 trigger 단서가 제시된 경우
    #         if fact.threshold <= state.current_pressure:
    #             revealed.append(fact)
    #         #
    #         # elif any(eid in state.clue_seen_ids for eid in secret.trigger_clue_ids):
    #         #     revealed.append(fact)
    #     return revealed
    #
    # def _format_facts(self, facts: List[FactSchema]) -> str:
    #     if not facts:
    #         return "- 공개할 사실 없음"
    #     lines = []
    #     for fact in facts:
    #         temp = None
    #         match fact.type:
    #             case "timeline":
    #                 temp = self._format_timeline(fact.content)
    #             case "secret":
    #                 temp = self._format_secrets(fact.content)
    #             case _:
    #                 temp =f"- {fact.model_dump_json()}"
    #         lines.append(temp)
    #
    #     return "\n".join(lines)
    #
    # def _format_timeline(self, timeline: dict) -> str:
    #     """타임라인을 문자열로 포맷"""
    #     return f"- {timeline["time"]}: {timeline["location"]}에서 {timeline["activity"]}"
    #
    # def _format_secrets(self, secrets: dict) -> str:
    #     """비밀 목록을 문자열로 포맷"""
    #     return f"- {secrets["content"]}"

    def _format_history(self, history: list) -> str:
        """대화 히스토리 포맷"""
        if not history:
            return "(대화 시작)"
        return "\n".join([f"{h['role']}: {h['content']}" for h in history])
