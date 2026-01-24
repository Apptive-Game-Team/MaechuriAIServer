"""Chat request schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class SuspectChatRequest(BaseModel):
    """Request for suspect chat (Stateful with GameSession)."""
    session_id: str = Field(description="Game session ID (UUID)")
    scenario_id: int = Field(description="Scenario ID")
    suspect_id: int = Field(description="Suspect ID to interrogate")
    user_message: str = Field(description="User's question/message")
    clue_id: Optional[int] = Field(default=None, description="Clue ID to present (optional)")


class ClueChatRequest(BaseModel):
    """Request for clue chat (Stateful with GameSession)."""
    session_id: str = Field(description="Game session ID (UUID)")
    scenario_id: int = Field(description="Scenario ID")
    clue_id: int = Field(description="Clue ID to analyze")
    user_message: str = Field(description="User's question/message")
