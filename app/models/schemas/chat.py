from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    """단일 대화 메시지"""
    role: Literal["user", "suspect", "detective"]
    content: str


class SuspectChatHistorySchema(BaseModel):
    """용의자 대화 히스토리 (세션 상태)"""
    chat_history: List[ChatMessageSchema] = Field(default_factory=list)
    pressure: int = Field(default=0, ge=0, le=100)
    evidence_seen_ids: List[int] = Field(default_factory=list)


class ClueChatHistorySchema(BaseModel):
    """증거 대화 히스토리"""
    chat_history: List[ChatMessageSchema] = Field(default_factory=list)


class SuspectChatRequest(BaseModel):
    """용의자 대화 요청"""
    scenario_id: int
    suspect_id: int
    user_message: str
    history: SuspectChatHistorySchema = Field(default_factory=SuspectChatHistorySchema)
    evidence_id: Optional[int] = None


class ClueChatRequest(BaseModel):
    """증거 대화 요청"""
    scenario_id: int
    clue_id: int
    user_message: str
    history: ClueChatHistorySchema = Field(default_factory=ClueChatHistorySchema)


class SuspectChatResponse(BaseModel):
    """용의자 대화 응답"""
    user_message: str
    answer: str
    pressure: int
    pressure_delta: int
    history: SuspectChatHistorySchema


class ClueChatResponse(BaseModel):
    """증거 대화 응답"""
    user_message: str
    answer: str
    history: ClueChatHistorySchema
