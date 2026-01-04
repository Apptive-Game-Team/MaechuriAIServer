from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class ClueItemSchema(BaseModel):
    name: str = Field(description="Short name of the clue")
    found_at: str = Field(description="The location where the clue is discovered - must be one of scenario.world.locations")
    description: str = Field(description="Detailed description of what the clue is and how it looks")
    related_suspect_ids: List[str] = Field(default=[], description="List of suspect IDs this clue points to or is associated with")
    logic_explanation: str = Field(description="Brief explanation of how this clue contributes to the logical deduction")
    is_red_herring: bool = Field(default=False, description="True if this clue is meant to mislead the player (Red Herring)")

class ClueSetSchema(BaseModel):
    clues: List[ClueItemSchema]
