from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.repositories.chat_repository import ChatRepository
from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.llm.gemini_client import GeminiClient
from app.services.npc.chat_service import ChatService
from app.services.agent.suspect_agent import SuspectAgent
from app.services.agent.clue_agent import ClueAgent

router = APIRouter(prefix="/chats", tags=["chats"])

# 요청 바디 정의
class SuspectChatRequest(BaseModel):
    scenario_id: int
    suspect_id: int
    user_id: int
    user_message: str

class ClueChatRequest(BaseModel):
    scenario_id: int
    clue_id: int
    user_id: int
    user_message: str

# ================= Dependency =================
def get_gemini() -> GeminiClient:
    return GeminiClient()

def get_chat_repository() -> ChatRepository:
    return ChatRepository()

def get_scenario_repository() -> ScenarioRepository:
    return ScenarioRepository()

def get_suspect_agent(
        llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> SuspectAgent:
    return SuspectAgent(llm_client)

def get_clue_agent(
        llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> ClueAgent:
    return ClueAgent(llm_client)

def get_chat_service(
    chat_repository: Annotated[ChatRepository, Depends(get_chat_repository)],
    scenario_repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
    suspect_agent: Annotated[SuspectAgent, Depends(get_suspect_agent)],
    clue_agent: Annotated[ClueAgent, Depends(get_clue_agent)]
) -> ChatService:
    return ChatService(chat_repository=chat_repository,
                       scenario_repository=scenario_repository,
                       suspect_agent=suspect_agent, 
                       clue_agent=clue_agent)
# ================= End =================

@router.post("/suspect")
async def chat_with_suspect(
        request: SuspectChatRequest,
        chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    용의자와 대화하는 API
    유저 id를 통해 db에 접속하여 대화 내용을 가져온 후 그것을 바탕으로 다음 대화를 진행한다.
    """
    return await chat_service.suspect_chat(**request.model_dump())

@router.post("/clue")
async def analyze_clue(
        request: ClueChatRequest,
        chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    경관과 대화하는 API
    유저 id를 통해 db에 접속하여 대화 내용을 가져온 후 그것을 바탕으로 다음 대화를 진행한다.
    """
    return await chat_service.clue_chat(**request.model_dump())