"""Map detail schemas for complete map output."""
from typing import List
from pydantic import BaseModel, Field
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


class FurnitureSchema(BaseModel):
    """Single furniture item placed in a room."""
    name: str = Field(description="Furniture name (e.g. 낡은 책상, 가죽 소파)")
    description: str = Field(description="Narrative description matching room theme")
    room_id: int = Field(ge=1, description="Room this furniture belongs to")
    origin_x: int = Field(ge=0)
    origin_y: int = Field(ge=0)
    width: int = Field(ge=1, le=4)
    height: int = Field(ge=1, le=4)


class RoomFurnitureSchema(BaseModel):
    """Collection of furniture items for all rooms."""
    furniture: List[FurnitureSchema]
