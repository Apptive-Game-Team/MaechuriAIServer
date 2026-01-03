from typing import Optional, Literal
from pydantic import BaseModel

from app.models.schemas.scenario import (
    TimeRangeSchema,
    WorldContextSchema,
    GroundTruthSchema,
    ConstraintsSchema,
    SuspectGenConfig
)

class CaseContextSchema(BaseModel):
    incident_time: TimeRangeSchema
    primary_location: str
    incident_type: Literal["theft", "murder", "sabotage"]
    summary: str

class SuspectGenerationRequest(BaseModel):
    case_context: CaseContextSchema
    world_context: WorldContextSchema
    ground_truth: GroundTruthSchema
    generation_config: SuspectGenConfig
    constraints: Optional[ConstraintsSchema] = None
