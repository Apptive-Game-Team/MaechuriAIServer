"""Ground truth schemas for the scenario solution."""
from typing import List
from pydantic import BaseModel, Field
from .common import TimeRangeSchema


class RequiredEvidenceSchema(BaseModel):
    """Evidence required to solve the case."""
    type: str
    min_count: int = Field(ge=1)


class GroundTruthSkeletonSchema(BaseModel):
    """Basic ground truth structure."""
    culprit_count: int = Field(ge=1)
    crime_time_range: TimeRangeSchema
    crime_location: str


class GroundTruthSchema(GroundTruthSkeletonSchema):
    """Detailed ground truth including culprits, method, and required evidence."""
    culprit_ids: List[int] = []
    method: str = ""
    required_evidence: List[RequiredEvidenceSchema] = []
