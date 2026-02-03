from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.npc.chat_service import ChatService
from app.api.dependencies.chat_dependencies import get_chat_service
from app.models.schemas.chat import (
    SuspectChatRequest,
    ClueChatRequest,
    GeneralChatRequest,
    SuspectChatResponse,
    ClueChatResponse,
    GeneralChatResponse
)

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.post("/suspect", response_model=SuspectChatResponse)
async def chat_with_suspect(
    request: SuspectChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SuspectChatResponse:
    """
    용의자와 심문 대화를 진행합니다 (Stateful with GameSession).

    - GameSession에서 게임 상태를 로드합니다 (pressure, evidence_seen 등).
    - Judge LLM이 유저 입력을 평가하여 pressure 변화량을 계산합니다.
    - Actor LLM이 현재 pressure에 맞는 용의자 응답을 생성합니다.
    - RAG를 통해 관련 과거 대화와 용의자 정보를 검색합니다.
    - 대화 후 GameSession을 업데이트하고 메시지를 RAG에 저장합니다.

    **단서 제시 형식:**
    - `[c:ID]`: 단서 참조 (예: "이 증거에 대해 어떻게 생각해? [c:1]")
    """
    return await chat_service.suspect_chat(
        session_id=request.session_id,
        scenario_id=request.scenario_id,
        suspect_id=request.suspect_id,
        user_message=request.user_message,
        db=db
    )


@router.post("/clue", response_model=ClueChatResponse, deprecated=True)
async def chat_with_clue(
    request: ClueChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ClueChatResponse:
    """
    증거와 대화합니다 (증거 분석, Stateful with GameSession).

    **Deprecated**: Use `/api/chats/general` with `[c:{clue_id}]` in user_message instead.

    - GameSession에서 게임 상태를 로드합니다.
    - RAG를 통해 관련 단서 정보와 과거 분석 내역을 검색합니다.
    - ClueAgent가 단서 분석 및 해석을 제공합니다.
    - 대화 후 GameSession을 업데이트하고 메시지를 RAG에 저장합니다.
    """
    return await chat_service.clue_chat(
        session_id=request.session_id,
        scenario_id=request.scenario_id,
        clue_id=request.clue_id,
        user_message=request.user_message,
        db=db
    )


@router.post("/general", response_model=GeneralChatResponse)
async def chat_with_detective(
    request: GeneralChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> GeneralChatResponse:
    """
    형사와 통합 대화를 진행합니다 (Stateful with GameSession).

    사건 질문과 단서/용의자 분석을 자연스럽게 처리합니다.
    참조된 단서/용의자 정보는 자동으로 RAG 컨텍스트에 포함됩니다.

    **참조 형식:**
    - `[c:ID]`: 단서 참조 (예: [c:1], [c:02])
    - `[s:ID]`: 용의자 참조 (예: [s:1], [s:02])

    **형사 응답 규칙:**
    - 범인, 살해 방법, 동기는 절대 공개하지 않음
    - 논리/추론 과정을 직접 설명하지 않음 (사용자가 추론하도록 유도)
    - 게임 메타 용어 사용 금지 ("힌트", "플레이어" 등)
    """
    return await chat_service.general_chat(
        session_id=request.session_id,
        scenario_id=request.scenario_id,
        user_message=request.user_message,
        db=db
    )
