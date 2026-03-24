"""Main scenario schema compositions."""
from typing import List, Optional
from pydantic import BaseModel
from ..clue import ClueItemSchema
from ..map import MapOutputSchema
from ..map.detail import FurnitureSchema
from ..suspect import SuspectSchema
from .meta import MetaSchema
from .incident import IncidentSchema
from .world import WorldSkeletonSchema, WorldContextSchema
from .ground_truth import GroundTruthSkeletonSchema, GroundTruthSchema
from .generation import GenerationTargetsSchema
from .constraints import ConstraintsSchema


class ScenarioSkeleton(BaseModel):
    """Basic scenario structure."""
    meta: MetaSchema
    incident: IncidentSchema
    world: WorldSkeletonSchema
    ground_truth: GroundTruthSkeletonSchema


class ScenarioExpansion(ScenarioSkeleton):
    """Expanded scenario with detailed world, ground truth, targets, and constraints."""
    world_detail: WorldContextSchema
    ground_truth_detail: GroundTruthSchema
    generation_targets: GenerationTargetsSchema
    constraints: ConstraintsSchema


class ScenarioExpansionRequest(BaseModel):
    """Request schema for scenario expansion."""
    world_detail: WorldContextSchema
    ground_truth_detail: GroundTruthSchema
    generation_targets: GenerationTargetsSchema
    constraints: ConstraintsSchema


class ExpansionPart1(BaseModel):
    """First part of expansion: world and ground truth details."""
    world_detail: WorldContextSchema
    ground_truth_detail: GroundTruthSchema


class ExpansionPart2(BaseModel):
    """Second part of expansion: generation targets and constraints."""
    generation_targets: GenerationTargetsSchema
    constraints: ConstraintsSchema


class ScenarioResult(ScenarioExpansion):
    """Complete scenario result with clues, map, suspects, and furniture."""
    clues: List[ClueItemSchema]
    map: Optional[MapOutputSchema] = None
    suspects: List[SuspectSchema] = []
    furniture: List[FurnitureSchema] = []
