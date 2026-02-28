"""Map detail schemas for complete map output."""
from typing import List
from pydantic import BaseModel
from .common import PositionSchema, MapObjectType
from .skeleton import RoomSkeletonSchema, CorridorSchema


class MapObjectSchema(BaseModel):
    """Map objects like clues and suspects."""
    id: int
    position: PositionSchema
    room_id: int
    type: MapObjectType


class MapOutputSchema(BaseModel):
    """Complete map output with rooms, corridors, and objects."""
    rooms: List[RoomSkeletonSchema]
    corridors: List[CorridorSchema]
    obj: List[MapObjectSchema]
