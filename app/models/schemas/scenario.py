from typing import List, Literal, Optional
from .map import MapOutputSchema
from datetime import time
from pydantic import BaseModel, Field

from .clue import ClueSetSchema

# --- Common ---
class TimeRangeSchema(BaseModel):
    start: time
    end: time

# --- Meta ---
class MetaSchema(BaseModel):
    difficulty: Literal["easy", "mid", "hard"]
    theme: str
    tone: str
    language: str = "ko"

# --- Incident ---
class IncidentSchema(BaseModel):
    type: str
    summary: str
    time_range: TimeRangeSchema
    location: str
    primary_object: str

# --- World ---
class VisibilityRuleSchema(BaseModel):
    from_location: str
    can_see: List[str]
    cannot_see: List[str]
    evidence_type: Optional[str] = None

class AccessRuleSchema(BaseModel):
    location: str
    requires: str

class WorldSkeletonSchema(BaseModel):
    locations: List[str]
    time_granularity_minutes: int = 5

class WorldContextSchema(WorldSkeletonSchema):
    visibility_rules: List[VisibilityRuleSchema] = []
    access_rules: Optional[List[AccessRuleSchema]] = []
    evidence_types: Optional[List[str]] = None

# --- Ground Truth ---
class RequiredEvidenceSchema(BaseModel):
    type: str
    min_count: int = Field(ge=1)

class GroundTruthSkeletonSchema(BaseModel):
    culprit_count: int = Field(ge=1)
    crime_time_range: TimeRangeSchema
    crime_location: str

class GroundTruthSchema(GroundTruthSkeletonSchema):
    culprit_ids: List[int] = []
    method: str = ""
    required_evidence: List[RequiredEvidenceSchema] = []

# --- Constraints ---
class ConstraintsSchema(BaseModel):
    no_supernatural: bool = True
    no_time_travel: bool = True
    at_least_one_uncertain_alibi: bool = False

# --- Generation Targets ---
class DetailedSuspect(BaseModel):
    id: int
    name: str
    role: str

class SuspectGenConfig(BaseModel):
    count: int = Field(ge=1)
    suspects: List[DetailedSuspect]
    allow_lying: bool
    liar_ratio: float = Field(ge=0.0, le=1.0)

class EvidenceGenConfig(BaseModel):
    count_range: List[int] = Field(min_length=2, max_length=2)
    ambiguity_level: Literal["low", "medium", "high"]

class GenerationTargetsSchema(BaseModel):
    suspects: SuspectGenConfig
    evidence: EvidenceGenConfig

# ===============================================================


# --- Scenario Main ---
class ScenarioSkeleton(BaseModel):
    meta: MetaSchema
    incident: IncidentSchema
    world: WorldSkeletonSchema
    ground_truth: GroundTruthSkeletonSchema

class ScenarioExpansion(ScenarioSkeleton):
    world_detail: WorldContextSchema
    ground_truth_detail: GroundTruthSchema
    generation_targets: GenerationTargetsSchema
    constraints: ConstraintsSchema

class ScenarioExpansionRequest(BaseModel):
    world_detail: WorldContextSchema
    ground_truth_detail: GroundTruthSchema
    generation_targets: GenerationTargetsSchema
    constraints: ConstraintsSchema

class ExpansionPart1(BaseModel):
    world_detail: WorldContextSchema
    ground_truth_detail: GroundTruthSchema

class ExpansionPart2(BaseModel):
    generation_targets: GenerationTargetsSchema
    constraints: ConstraintsSchema

class ScenarioResult(ScenarioExpansion):
    clues: ClueSetSchema
    map: MapOutputSchema | dict = {}

