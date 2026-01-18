"""Scenario constraint schemas."""
from pydantic import BaseModel


class ConstraintsSchema(BaseModel):
    """Constraints for scenario generation."""
    no_supernatural: bool = True
    no_time_travel: bool = True
    at_least_one_uncertain_alibi: bool = False
