from typing import List, Literal
from pydantic import BaseModel


class PositionSchema(BaseModel):
    x: int
    y: int


# === Map Skeleton Schemas ===

class RoomSkeletonSchema(BaseModel):
    """방 기본 정보 (Skeleton용)"""
    id: int
    name: str
    width: int
    height: int
    mood: str


class CorridorConnectionSchema(BaseModel):
    """복도와 방의 연결 정보"""
    room_id: int
    direction: Literal["north", "south", "east", "west"]  # 이 방에서 복도로 나가는 방향


class CorridorSchema(BaseModel):
    """복도 정보 (연결 + 방향 + 크기 힌트)"""
    id: int
    name: str
    connections: List[CorridorConnectionSchema]  # 연결된 방들과 각 방향
    width_hint: int   # 복도 폭 힌트 (타일 단위)
    length_hint: int  # 복도 길이 힌트 (타일 단위)


class MapSkeletonSchema(BaseModel):
    """Map Skeleton: 공간 구조 정보"""
    rooms: List[RoomSkeletonSchema]
    corridors: List[CorridorSchema]


# === Map Detail Schemas ===

class RoomSchema(BaseModel):
    """방 상세 정보 (Detail용)"""
    id: int
    name: str
    width: int
    height: int
    mood: str


class MapObjectSchema(BaseModel):
    """맵 오브젝트 (단서, 용의자 등)"""
    id: int
    name: str
    position: PositionSchema
    room_id: int
    type: str


class MapOutputSchema(BaseModel):
    """Map Detail: 최종 맵 출력"""
    rooms: List[RoomSchema]
    corridors: List[CorridorSchema]
    obj: List[MapObjectSchema]