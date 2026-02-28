"""Common map schemas and type literals."""
from typing import Literal
from pydantic import BaseModel

MapElementType = Literal["room", "corridor"]
MapObjectType = Literal["suspect", "clue"]


class PositionSchema(BaseModel):
    """Position coordinates on the map."""
    x: int
    y: int
