"""Chat response schemas."""
from pydantic import BaseModel, Field


class SuspectChatResponse(BaseModel):
    """Response for suspect chat (Stateful - no history returned)."""
    user_message: str = Field(description="User's question (echo)")
    answer: str = Field(description="Suspect's response")
    pressure: int = Field(description="Current pressure level (0-100)")
    pressure_delta: int = Field(description="Pressure change from this interaction")


class ClueChatResponse(BaseModel):
    """Response for clue chat (Stateful - no history returned)."""
    user_message: str = Field(description="User's question (echo)")
    answer: str = Field(description="Detective's analysis of the clue")
