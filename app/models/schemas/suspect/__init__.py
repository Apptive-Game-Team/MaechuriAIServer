"""Suspect schema modules organized by purpose."""
from .common import (
    TimelineEntrySchema,
    SecretTierSchema,
    PersonalitySchema
)
from .request import (
    CaseContextSchema,
    SuspectGenerationRequest
)
from .response import (
    SuspectSchema,
    SuspectListSchema
)

__all__ = [
    # Common
    "TimelineEntrySchema",
    "SecretTierSchema",
    "PersonalitySchema",
    # Request
    "CaseContextSchema",
    "SuspectGenerationRequest",
    # Response
    "SuspectSchema",
    "SuspectListSchema",
]
