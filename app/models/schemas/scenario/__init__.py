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
    RequiredClueSchema,
    GroundTruthSkeletonSchema,
    GroundTruthSchema
)
from .constraints import ConstraintsSchema
from .generation import (
    DetailedSuspect,
    SuspectGenConfig,
    ClueGenConfig,
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
    "RequiredClueSchema",
    "GroundTruthSkeletonSchema",
    "GroundTruthSchema",
    # Constraints
    "ConstraintsSchema",
    # Generation
    "DetailedSuspect",
    "SuspectGenConfig",
    "ClueGenConfig",
    "GenerationTargetsSchema",
    # Main
    "ScenarioSkeleton",
    "ScenarioExpansion",
    "ScenarioExpansionRequest",
    "ExpansionPart1",
    "ExpansionPart2",
    "ScenarioResult",
]
