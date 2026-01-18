"""Chat response schemas."""
from pydantic import BaseModel
from .common import SuspectChatHistorySchema, ClueChatHistorySchema


class SuspectChatResponse(BaseModel):
    """Response for suspect chat."""
    user_message: str
    answer: str
    pressure: int
    pressure_delta: int
    history: SuspectChatHistorySchema


class ClueChatResponse(BaseModel):
    """Response for clue chat."""
    user_message: str
    answer: str
    history: ClueChatHistorySchema
