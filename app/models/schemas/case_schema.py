from pydantic import BaseModel
from typing import Literal

from .common import TimeRangeSchema

class CaseContextSchema(BaseModel):
    incident_time: TimeRangeSchema
    primary_location: str
    incident_type: Literal["theft", "murder", "sabotage"]
    summary: str
