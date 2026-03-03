"""Map skeleton schemas for basic structure."""
from typing import List, Literal
from pydantic import BaseModel


class RoomSkeletonSchema(BaseModel):
    """Basic room information for skeleton."""
    id: int
    name: str
    width: int
    height: int
    mood: str
    x: int
    y: int


class CorridorConnectionSchema(BaseModel):
    """Connection between corridor and room."""
    room_id: int
    direction: Literal["north", "south", "east", "west"]


class CorridorSchema(BaseModel):
    """Corridor information with connections and size hints."""
    id: int
    name: str
    connections: List[CorridorConnectionSchema]
    width_hint: int
    length_hint: int
    x: int
    y: int
    width: int
    height: int


class MapSkeletonSchema(BaseModel):
    """Map skeleton with spatial structure."""
    rooms: List[RoomSkeletonSchema]
    corridors: List[CorridorSchema]
