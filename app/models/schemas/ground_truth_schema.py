from pydantic import BaseModel, Field
from typing import List
from .common import TimeRangeSchema

class RequiredEvidenceSchema(BaseModel):
    type: str
    min_count: int = Field(ge=1)


class GroundTruthSchema(BaseModel):
    culprit_count: int = Field(ge=1)
    crime_time_range: TimeRangeSchema
    crime_location: str
    method: str
    required_evidence: List[RequiredEvidenceSchema]
