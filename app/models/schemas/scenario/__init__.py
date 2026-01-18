"""Scenario schema modules organized by concern."""
from .common import TimeRangeSchema
from .meta import MetaSchema
from .incident import IncidentSchema
from .world import (
    VisibilityRuleSchema,
    AccessRuleSchema,
    WorldSkeletonSchema,
    WorldContextSchema
)
from .ground_truth import (
    RequiredEvidenceSchema,
    GroundTruthSkeletonSchema,
    GroundTruthSchema
)
from .constraints import ConstraintsSchema
from .generation import (
    DetailedSuspect,
    SuspectGenConfig,
    EvidenceGenConfig,
    GenerationTargetsSchema
)
from .main import (
    ScenarioSkeleton,
    ScenarioExpansion,
    ScenarioExpansionRequest,
    ExpansionPart1,
    ExpansionPart2,
    ScenarioResult
)

__all__ = [
    # Common
    "TimeRangeSchema",
    # Meta
    "MetaSchema",
    # Incident
    "IncidentSchema",
    # World
    "VisibilityRuleSchema",
    "AccessRuleSchema",
    "WorldSkeletonSchema",
    "WorldContextSchema",
    # Ground Truth
    "RequiredEvidenceSchema",
    "GroundTruthSkeletonSchema",
    "GroundTruthSchema",
    # Constraints
    "ConstraintsSchema",
    # Generation
    "DetailedSuspect",
    "SuspectGenConfig",
    "EvidenceGenConfig",
    "GenerationTargetsSchema",
    # Main
    "ScenarioSkeleton",
    "ScenarioExpansion",
    "ScenarioExpansionRequest",
    "ExpansionPart1",
    "ExpansionPart2",
    "ScenarioResult",
]
