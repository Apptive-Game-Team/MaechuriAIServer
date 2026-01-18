"""Incident-related schemas."""
from pydantic import BaseModel
from .common import TimeRangeSchema


class IncidentSchema(BaseModel):
    """Incident information including type, summary, time, and location."""
    type: str
    summary: str
    time_range: TimeRangeSchema
    location: str
    primary_object: str
