from typing import List, Literal
from pydantic import BaseModel, Field, field_validator

class GenerationConfigSchema(BaseModel):
    suspect_count: int = Field(ge=1)
    difficulty: Literal["easy", "mid", "hard"]
    anchor_events_range: List[int] = Field(min_length=2, max_length=2)
    routines_range: List[int] = Field(min_length=2, max_length=2)
    allow_lying: bool
    liar_ratio: float = Field(ge=0.0, le=1.0)
    ambiguity_level: Literal["low", "medium", "high"]

    @field_validator("anchor_events_range", "routines_range")
    @classmethod
    def validate_anchor_events_range(cls, v):
        if v[0] > v[1]:
            raise ValueError("range must be [min, max] with min <= max")
        return v

    @field_validator("liar_ratio")
    @classmethod
    def validate_liar_ratio(cls, v, info):
        if not info.data.get("allow_lying") and v != 0.0:
            raise ValueError("liar_ratio must 0.0 when allow_lying is False")
        return v