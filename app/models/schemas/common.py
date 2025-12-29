from pydantic import BaseModel
from datetime import time

class TimeRangeSchema(BaseModel):
    start: time
    end: time