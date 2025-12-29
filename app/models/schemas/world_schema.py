from pydantic import BaseModel, Field
from typing import List, Optional

class VisibilityRuleSchema(BaseModel):
    from_location: str = Field(alias="from")
    can_see: List[str]
    cannot_see: List[str]
    evidence_type: Optional[str] = None


class AccessRuleSchema(BaseModel):
    location: str
    requires: str


class WorldContextSchema(BaseModel):
    locations: List[str]
    visibility_rules: List[VisibilityRuleSchema]
    access_rules: Optional[List[AccessRuleSchema]] = []
    evidence_types: List[str]
