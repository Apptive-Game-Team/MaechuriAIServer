"""Common chat schemas."""
from typing import List, Literal
from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    """Single chat message."""
    role: Literal["user", "suspect", "detective"]
    content: str


class SuspectChatHistorySchema(BaseModel):
    """Chat history for suspect conversations."""
    chat_history: List[ChatMessageSchema] = Field(default_factory=list)
    pressure: int = Field(default=0, ge=0, le=100)
    evidence_seen_ids: List[int] = Field(default_factory=list)


class ClueChatHistorySchema(BaseModel):
    """Chat history for clue conversations."""
    chat_history: List[ChatMessageSchema] = Field(default_factory=list)
