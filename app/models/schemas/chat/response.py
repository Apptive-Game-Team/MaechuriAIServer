"""Chat response schemas."""
from typing import List

from pydantic import BaseModel, Field


class SuspectChatResponse(BaseModel):
    """Response for suspect chat (Stateful - no history returned)."""
    user_message: str = Field(description="User's question (echo)")
    answer: str = Field(description="Suspect's response")
    pressure: int = Field(description="Current pressure level (0-100)")
    pressure_delta: int = Field(description="Pressure change from this interaction")
    revealed_fact_ids: List[int] = Field(description="Fact IDs revealed at current pressure level (threshold <= pressure)")


class ClueChatResponse(BaseModel):
    """Response for clue chat (Stateful - no history returned).

    Deprecated: Use GeneralChatResponse instead. Clue analysis is now handled
    seamlessly through general_chat with automatic clue detection.
    """
    user_message: str = Field(description="User's question (echo)")
    answer: str = Field(description="Detective's analysis of the clue")


class GeneralChatResponse(BaseModel):
    """Response for general detective chat.

    Handles case discussion and clue analysis in a unified flow.
    When clues are referenced via [c:ID], their info is included in context.
    """
    user_message: str = Field(description="User's question (echo)")
    answer: str = Field(description="Detective's response")
