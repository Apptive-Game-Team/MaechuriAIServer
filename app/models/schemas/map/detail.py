"""Map detail schemas for complete map output."""
from typing import List
from pydantic import BaseModel
from .common import PositionSchema
from .skeleton import CorridorSchema


class RoomSchema(BaseModel):
    """Detailed room information."""
    id: int
    name: str
    width: int
    height: int
    mood: str


class MapObjectSchema(BaseModel):
    """Map objects like clues and suspects."""
    id: int
    name: str
    position: PositionSchema
    room_id: int
    type: str


class MapOutputSchema(BaseModel):
    """Complete map output with rooms, corridors, and objects."""
    rooms: List[RoomSchema]
    corridors: List[CorridorSchema]
    obj: List[MapObjectSchema]
