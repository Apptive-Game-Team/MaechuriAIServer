"""Map schema modules organized by structure."""
from .common import PositionSchema, MapElementType, MapObjectType
from .skeleton import (
    RoomSkeletonSchema,
    CorridorConnectionSchema,
    CorridorSchema,
    MapSkeletonSchema
)
from .detail import (
    MapObjectSchema,
    MapOutputSchema
)

__all__ = [
    # Common
    "PositionSchema",
    "MapElementType",
    "MapObjectType",
    # Skeleton
    "RoomSkeletonSchema",
    "CorridorConnectionSchema",
    "CorridorSchema",
    "MapSkeletonSchema",
    # Detail
    "MapObjectSchema",
    "MapOutputSchema",
]
