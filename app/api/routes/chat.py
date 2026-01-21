from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.npc.chat_service import ChatService
from app.api.dependencies.chat_dependencies import get_chat_service
from app.models.schemas.chat import (
    SuspectChatRequest,
    ClueChatRequest,
    SuspectChatResponse,
    ClueChatResponse
)

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.post("/suspect", response_model=SuspectChatResponse)
async def chat_with_suspect(
    request: SuspectChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SuspectChatResponse:
    """
    용의자와 심문 대화를 진행합니다.

    - Judge LLM이 유저 입력을 평가하여 pressure 변화량을 계산합니다.
    - Actor LLM이 현재 pressure에 맞는 용의자 응답을 생성합니다.
    - evidence_id를 전달하면 해당 증거를 제시합니다.
    - session_id를 전달하면 RAG를 통해 관련 과거 대화를 검색합니다.
    """
    return await chat_service.suspect_chat(
        scenario_id=request.scenario_id,
        suspect_id=request.suspect_id,
        user_message=request.user_message,
        history=request.history,
        evidence_id=request.evidence_id,
        db=db,
        session_id=request.session_id
    )


@router.post("/clue", response_model=ClueChatResponse)
async def chat_with_clue(
    request: ClueChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ClueChatResponse:
    """
    증거와 대화합니다 (증거 분석).

    - session_id를 전달하면 RAG를 통해 관련 과거 대화를 검색합니다.
    """
    return await chat_service.clue_chat(
        scenario_id=request.scenario_id,
        clue_id=request.clue_id,
        user_message=request.user_message,
        history=request.history,
        db=db,
        session_id=request.session_id
    )
