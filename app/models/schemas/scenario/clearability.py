"""Schema for scenario clearability evaluation output."""
from pydantic import BaseModel, Field


class ClearabilityEvaluation(BaseModel):
    """LLM output for whether a scenario is clearable within 10 turns."""
    is_clearable: bool = Field(
        description="True if a player can logically deduce the killer within 10 conversation turns."
    )
    reason: str = Field(
        description="Brief explanation of the expected logical path or why it failed."
    )
