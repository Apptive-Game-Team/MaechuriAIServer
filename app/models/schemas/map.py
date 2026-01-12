from typing import List, Literal
from pydantic import BaseModel

class PositionSchema(BaseModel):
    x: int
    y: int

class RoomSchema(BaseModel):
    id: int
    name: str
    width: int
    height: int
    mood: str

class MapObjectSchema(BaseModel):
    id: int
    name: str
    position: PositionSchema
    room_id: int
    type: str

class MapOutputSchema(BaseModel):
    rooms: List[RoomSchema]
    obj: List[MapObjectSchema]