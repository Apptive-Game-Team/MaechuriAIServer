from typing import Optional

from app.core.utils import extract_json, safe_json_load
from app.services.llm.llm_client import LLMClient
from app.services.prompt.prompt_loader import PromptLoader
from app.services.npc.formatters import ChatFormatter
from app.models.schemas.suspect import SuspectSchema
from app.models.schemas.suspect_responder import SuspectActorOutput
from app.models.domain.suspect_state import SuspectState


class SuspectActor:
    """
    Judge + Actor를 단일 LLM 호출로 통합한 에이전트.
    pressure 평가와 인캐릭터 응답을 동시에 생성하여 레이턴시를 줄임.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.system_prompt_template = PromptLoader.load("app/prompts/suspect_responder/system.txt")

    async def arespond(
        self,
        user_message: str,
        suspect: SuspectSchema,
        state: SuspectState,
        clue_presented: Optional[dict] = None,
        rag_context: Optional[str] = None,
        suspect_facts: str = "",
    ) -> SuspectActorOutput:
        """
        단일 LLM 호출로 pressure 평가 + 응답 생성.

        Args:
            user_message: 유저가 보낸 메시지
            suspect: 용의자 스키마 데이터
            state: 현재 런타임 상태 (pressure 등)
            clue_presented: 제시된 단서 (있다면)
            rag_context: RAG로 검색된 관련 컨텍스트
            suspect_facts: 포맷팅된 용의자 사실 정보

        Returns:
            SuspectActorOutput: pressure_delta + reasoning + response
        """
        prompt_data = ChatFormatter.build_suspect_prompt_data(
            suspect=suspect, state=state,
            clue_presented=clue_presented, rag_context=rag_context,
            suspect_facts=suspect_facts,
        )

        formatted_prompt = self.system_prompt_template.format(**prompt_data)

        raw = await self.llm.acomplete(
            system=formatted_prompt,
            user=user_message,
            response_schema=SuspectActorOutput.model_json_schema()
        )

        json_text = extract_json(raw)
        data = safe_json_load(json_text)

        return SuspectActorOutput.model_validate(data)
