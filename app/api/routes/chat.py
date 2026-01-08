from typing import Annotated

from fastapi import APIRouter, Depends

from app.services.npc.chat_service import ChatService
from app.api.dependencies.chat_dependencies import get_chat_service
from app.models.schemas.chat import SuspectChatRequest, ClueChatRequest, ChatResponse

router = APIRouter(prefix="/api/chats", tags=["chats"])

@router.post("/suspect")
async def chat_with_suspect(
        request: SuspectChatRequest,
        chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    answer = await chat_service.suspect_chat(**request.model_dump())

    return ChatResponse(
        user_message=request.user_message,
        history=request.history,
        answer=answer
    )


@router.post("/clue")
async def chat_with_clue(
        request: ClueChatRequest,
        chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    경관과 대화하는 API
    유저 id를 통해 db에 접속하여 대화 내용을 가져온 후 그것을 바탕으로 다음 대화를 진행한다.
    """
    answer = await chat_service.clue_chat(**request.model_dump())

    return ChatResponse(
        user_message=request.user_message,
        history=request.history,
        answer=answer
    )