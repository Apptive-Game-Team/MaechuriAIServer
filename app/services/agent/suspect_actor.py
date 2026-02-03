import json
from typing import Optional

from app.services.prompt.prompt_loader import PromptLoader
from app.services.rag.context_builder import get_context_builder, ContextBuilder
from app.models.schemas.suspect import SuspectSchema
from app.models.domain.suspect_state import SuspectState


class SuspectActor:
    """
    용의자를 연기하며 대화를 생성하는 Actor LLM.
    현재 pressure와 공개된 비밀을 기반으로 응답 생성.
    """

    def __init__(self, llm_client, context_builder: Optional[ContextBuilder] = None):
        self.llm = llm_client
        self.context_builder = context_builder or get_context_builder()
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

        # 프롬프트 데이터 구성
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
            "clue_presented": json.dumps(clue_presented, ensure_ascii=False) if clue_presented else "None",
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
