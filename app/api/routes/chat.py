from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.npc.chat_service import ChatService
from app.api.dependencies.chat_dependencies import get_chat_service

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