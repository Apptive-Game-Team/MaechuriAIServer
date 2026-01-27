"""Suspect schema modules organized by purpose."""
from .main import (
    SuspectSchema,
    SuspectListSchema
)
from .common import (
    FactSchema,
    FactEntrySchema,
    TimelineContentSchema,
    SecretContentSchema,
    PersonalitySchema
)
from .request import (
    CaseContextSchema,
    SuspectGenerationRequest
)
from .response import (
    SuspectGenerationSchema,
    SuspectGenerationListSchema
)

__all__ = [
    # Main
    "SuspectSchema",
    "SuspectListSchema",
    # Common
    "FactSchema",
    "TimelineContentSchema",
    "SecretContentSchema",
    "PersonalitySchema",
    "FactEntrySchema",
    # Request
    "CaseContextSchema",
    "SuspectGenerationRequest",
    # Response
    "SuspectGenerationSchema",
    "SuspectGenerationListSchema",
]
