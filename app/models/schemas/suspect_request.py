from typing import Optional
from pydantic import BaseModel

from app.models.schemas import (
    CaseContextSchema,
    WorldContextSchema,
    GroundTruthSchema,
    GenerationConfigSchema,
    ConstraintsSchema,
)

class SuspectGenerationRequest(BaseModel):
    case_context: CaseContextSchema
    world_context: WorldContextSchema
    ground_truth: GroundTruthSchema
    generation_config: GenerationConfigSchema
    constraints: Optional[ConstraintsSchema] = None
