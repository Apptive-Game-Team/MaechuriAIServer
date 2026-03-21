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
        knowledge_context: str = "",
    ) -> SuspectActorOutput:
        """Single LLM call: pressure evaluation + in-character response.

        Args:
            user_message: Detective message
            suspect: Suspect schema data
            state: Current runtime state (pressure etc.)
            clue_presented: Clue being presented (if any)
            knowledge_context: Structured knowledge context from build_suspect_knowledge_context()

        Returns:
            SuspectActorOutput: pressure_delta + reasoning + response
        """
        prompt_data = ChatFormatter.build_suspect_prompt_data(
            suspect=suspect, state=state,
            clue_presented=clue_presented,
            knowledge_context=knowledge_context,
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
