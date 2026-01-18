"""Common map schemas."""
from pydantic import BaseModel


class PositionSchema(BaseModel):
    """Position coordinates on the map."""
    x: int
    y: int
