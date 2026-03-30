"""Data Transfer Objects (DTOs) for the MaechuriAIServer API.

This package contains **Pydantic models** that are used exclusively for
API request/response serialisation and inter-service communication.
They are *not* ORM entities and carry no persistence logic.

Object-type boundaries
----------------------
DTOs (this package — ``app.models.schemas``)
    Pydantic ``BaseModel`` subclasses.  Used at the API boundary (FastAPI
    routes) and passed between service methods.  Prefixed ``*Schema``,
    ``*Request``, or ``*Response``.

Entities (``app.db.models``)
    SQLAlchemy ORM models.  Represent persistent database rows.  Never
    exposed directly to the API layer.

Domain objects (``app.models.domain``)
    Plain Python classes / dataclasses holding runtime business state that
    is not persisted directly (e.g. :class:`SuspectState`, :class:`Suspect`
    in-memory representation during interrogation).
"""
from .scenario import (
    TimeRangeSchema,
    MetaSchema,
    IncidentSchema,
    VisibilityRuleSchema,
    AccessRuleSchema,
    WorldSkeletonSchema,
    WorldContextSchema,
    RequiredClueSchema,
    GroundTruthSkeletonSchema,
    GroundTruthSchema,
    ConstraintsSchema,
    SuspectGenConfig,
    ClueGenConfig,
    GenerationTargetsSchema,
    ScenarioSkeleton,
    ScenarioExpansion,
    ScenarioResult
)

from .suspect import (
    CaseContextSchema,
    SuspectGenerationRequest
)

from .clue import (
    ClueItemSchema,
    ClueSetSchema
)

__all__ = [
    "TimeRangeSchema",
    "MetaSchema",
    "IncidentSchema",
    "VisibilityRuleSchema",
    "AccessRuleSchema",
    "WorldSkeletonSchema",
    "WorldContextSchema",
    "RequiredClueSchema",
    "GroundTruthSkeletonSchema",
    "GroundTruthSchema",
    "ConstraintsSchema",
    "SuspectGenConfig",
    "ClueGenConfig",
    "GenerationTargetsSchema",
    "ScenarioSkeleton",
    "ScenarioExpansion",
    "ScenarioResult",
    "CaseContextSchema",
    "SuspectGenerationRequest",
    "ClueItemSchema",
    "ClueSetSchema",
]
