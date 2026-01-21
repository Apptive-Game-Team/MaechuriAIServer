"""Chat request schemas."""
from typing import Optional
from pydantic import BaseModel, Field
from .common import SuspectChatHistorySchema, ClueChatHistorySchema


class SuspectChatRequest(BaseModel):
    """Request for suspect chat."""
    scenario_id: int
    suspect_id: int
    user_message: str
    history: SuspectChatHistorySchema = Field(default_factory=SuspectChatHistorySchema)
    evidence_id: Optional[int] = None
    session_id: Optional[str] = None  # For RAG history tracking


class ClueChatRequest(BaseModel):
    """Request for clue chat."""
    scenario_id: int
    clue_id: int
    user_message: str
    history: ClueChatHistorySchema = Field(default_factory=ClueChatHistorySchema)
    session_id: Optional[str] = None  # For RAG history tracking
