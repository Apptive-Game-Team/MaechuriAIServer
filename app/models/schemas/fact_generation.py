from pydantic import BaseModel, Field


class GeneratedGlobalFact(BaseModel):
    """Structured output for creating a new scenario-level fact."""

    text: str = Field(
        description="Canonical Korean fact text to add to the scenario."
    )
    reasoning: str = Field(
        description="Why this fact is consistent with the full scenario."
    )
