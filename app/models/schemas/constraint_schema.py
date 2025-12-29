from pydantic import BaseModel
from typing import List, Optional

class ConstraintItemSchema(BaseModel):
    type: str
    time: Optional[str] = None
    time_range: Optional[List[str]] = None
    evidence: Optional[str] = None


class ConstraintsSchema(BaseModel):
    must_have: Optional[List[ConstraintItemSchema]] = []
    must_not: Optional[List[ConstraintItemSchema]] = []
