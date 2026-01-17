from typing import List, Optional
from pydantic import BaseModel, Field

class ClueItemSchema(BaseModel):
    id: int = Field(description="Unique numeric identifier for the clue (1, 2, 3...)")
    name: str = Field(description="Short name of the clue")
    found_at: str = Field(description="The location where the clue is discovered - must be one of scenario.world.locations")
    description: str = Field(description="Detailed description of what the clue is and how it looks")
    related_suspect_ids: List[int] = Field(default=[], description="List of suspect IDs (integers) this clue points to")
    logic_explanation: str = Field(description="Brief explanation of how this clue contributes to the logical deduction")
    decoded_answer: Optional[str] = Field(default=None, description="The decoded/analyzed answer that the detective reveals when player makes correct deduction")
    is_red_herring: bool = Field(default=False, description="True if this clue is meant to mislead the player (Red Herring)")

class ClueSetSchema(BaseModel):
    clues: List[ClueItemSchema]
