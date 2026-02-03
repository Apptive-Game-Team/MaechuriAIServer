"""Chat request schemas."""
from pydantic import BaseModel, Field


class SuspectChatRequest(BaseModel):
    """Request for suspect chat (Stateful with GameSession).

    Use [c:ID] in user_message to present clues.
    Example: "이 증거에 대해 어떻게 생각해? [c:1]"
    """
    session_id: str = Field(description="Game session ID (UUID)")
    scenario_id: int = Field(description="Scenario ID")
    suspect_id: int = Field(description="Suspect ID to interrogate")
    user_message: str = Field(
        description="User's message. Use [c:ID] to present clues (e.g., [c:1])"
    )


class ClueChatRequest(BaseModel):
    """Request for clue chat (Stateful with GameSession).

    Deprecated: Use GeneralChatRequest with [c:{clue_id}] in user_message instead.
    """
    session_id: str = Field(description="Game session ID (UUID)")
    scenario_id: int = Field(description="Scenario ID")
    clue_id: int = Field(description="Clue ID to analyze")
    user_message: str = Field(description="User's question/message")


class GeneralChatRequest(BaseModel):
    """Request for general detective chat (unified conversation).

    Supports natural clue analysis via [c:ID] references in user_message.
    The AI automatically detects clue references and switches to analysis mode.

    Examples:
        - General: "사건이 언제 일어났어요?"
        - Clue analysis: "[c:1] 이 단서가 무슨 의미야?"
        - Suspect inquiry: "[s:1] 이 용의자에 대해 알려줘"
    """
    session_id: str = Field(description="Game session ID (UUID)")
    scenario_id: int = Field(description="Scenario ID")
    user_message: str = Field(
        description="User's message. Use [c:ID] for clue refs, [s:ID] for suspect refs."
    )
