"""Generation configuration schemas for suspects and evidence."""
from typing import List, Literal
from pydantic import BaseModel, Field


class DetailedSuspect(BaseModel):
    """Detailed suspect information for generation."""
    id: int
    name: str
    role: str


class SuspectGenConfig(BaseModel):
    """Configuration for suspect generation."""
    count: int = Field(ge=1)
    suspects: List[DetailedSuspect]
    allow_lying: bool
    liar_ratio: float = Field(ge=0.0, le=1.0)


class EvidenceGenConfig(BaseModel):
    """Configuration for evidence generation."""
    count_range: List[int] = Field(min_length=2, max_length=2)
    ambiguity_level: Literal["low", "medium", "high"]


class GenerationTargetsSchema(BaseModel):
    """Generation targets for suspects and evidence."""
    suspects: SuspectGenConfig
    evidence: EvidenceGenConfig
