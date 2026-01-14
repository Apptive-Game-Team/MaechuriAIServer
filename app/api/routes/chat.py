from typing import Annotated

from fastapi import APIRouter, Depends

from app.services.npc.chat_service import ChatService
from app.api.dependencies.chat_dependencies import get_chat_service
from app.models.schemas.chat import (
    SuspectChatRequest,
    ClueChatRequest,
    SuspectChatResponse,
    ChatResponse
)

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.post("/suspect", response_model=SuspectChatResponse)
async def chat_with_suspect(
    request: SuspectChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    용의자와 심문 대화를 진행합니다.

    - Judge LLM이 유저 입력을 평가하여 pressure 변화량을 계산합니다.
    - Actor LLM이 현재 pressure에 맞는 용의자 응답을 생성합니다.
    - evidence_id를 전달하면 해당 증거를 제시합니다.

    Returns:
        - answer: 용의자의 응답
        - pressure: 현재 압박 수치 (0-100)
        - pressure_delta: 이번 턴의 압박 변화량
        - tier: 현재 압박 단계 (CALM/NERVOUS/CORNERED/BREAKDOWN)
        - history: 업데이트된 대화 히스토리
    """
    result = await chat_service.suspect_chat(
        scenario_id=request.scenario_id,
        suspect_id=request.suspect_id,
        user_message=request.user_message,
        history=request.history,
        evidence_id=request.evidence_id
    )

    return SuspectChatResponse(
        user_message=request.user_message,
        answer=result["answer"],
        pressure=result["pressure"],
        pressure_delta=result["pressure_delta"],
        tier=result["tier"],
        history=result["history"]
    )


@router.post("/clue", response_model=ChatResponse)
async def chat_with_clue(
    request: ClueChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    증거와 대화합니다 (증거 분석).
    """
    answer = await chat_service.clue_chat(
        scenario_id=request.scenario_id,
        clue_id=request.clue_id,
        user_message=request.user_message,
        history=request.history
    )

    return ChatResponse(
        user_message=request.user_message,
        history=request.history,
        answer=answer
    )
