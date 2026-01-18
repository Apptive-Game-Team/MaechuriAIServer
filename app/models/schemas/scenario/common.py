"""Common schemas used across scenario components."""
from datetime import time
from pydantic import BaseModel


class TimeRangeSchema(BaseModel):
    """Time range with start and end times."""
    start: time
    end: time
