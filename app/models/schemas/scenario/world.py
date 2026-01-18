"""World context and rules schemas."""
from typing import List, Optional
from pydantic import BaseModel


class VisibilityRuleSchema(BaseModel):
    """Rules for what can or cannot be seen from a location."""
    from_location: str
    can_see: List[str]
    cannot_see: List[str]
    evidence_type: Optional[str] = None


class AccessRuleSchema(BaseModel):
    """Rules for accessing specific locations."""
    location: str
    requires: str


class WorldSkeletonSchema(BaseModel):
    """Basic world structure with locations and time granularity."""
    locations: List[str]
    time_granularity_minutes: int = 5


class WorldContextSchema(WorldSkeletonSchema):
    """Detailed world context including visibility and access rules."""
    visibility_rules: List[VisibilityRuleSchema] = []
    access_rules: Optional[List[AccessRuleSchema]] = []
    evidence_types: Optional[List[str]] = None
