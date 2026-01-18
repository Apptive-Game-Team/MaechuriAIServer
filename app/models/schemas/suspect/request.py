"""Request schemas for suspect generation."""
from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel
from app.models.schemas.clue import ClueItemSchema
from app.models.schemas.map import MapSkeletonSchema
from app.models.schemas.scenario import (
    TimeRangeSchema,
    WorldContextSchema,
    GroundTruthSchema,
    ConstraintsSchema,
    SuspectGenConfig
)

if TYPE_CHECKING:
    from app.models.schemas.scenario import ScenarioExpansion


class CaseContextSchema(BaseModel):
    """Case context for suspect generation."""
    incident_time: TimeRangeSchema
    primary_location: str
    incident_type: str
    summary: str


class SuspectGenerationRequest(BaseModel):
    """Request to generate suspects."""
    case_context: CaseContextSchema
    world_context: WorldContextSchema
    ground_truth: GroundTruthSchema
    generation_config: SuspectGenConfig
    clues: List[ClueItemSchema] = []
    constraints: Optional[ConstraintsSchema] = None
    map_skeleton: Optional[MapSkeletonSchema] = None

    @classmethod
    def from_expansion(
        cls,
        expansion: ScenarioExpansion,
        clues: List[ClueItemSchema] = [],
        map_skeleton: Optional[MapSkeletonSchema] = None
    ) -> SuspectGenerationRequest:
        """Create request from ScenarioExpansion."""
        return cls(
            case_context=CaseContextSchema(
                incident_time=expansion.incident.time_range,
                primary_location=expansion.incident.location,
                incident_type=expansion.incident.type,
                summary=expansion.incident.summary
            ),
            world_context=expansion.world_detail,
            ground_truth=expansion.ground_truth_detail,
            generation_config=expansion.generation_targets.suspects,
            clues=clues,
            constraints=expansion.constraints,
            map_skeleton=map_skeleton
        )
