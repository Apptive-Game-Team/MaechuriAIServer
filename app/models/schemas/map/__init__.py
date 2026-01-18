"""Map schema modules organized by structure."""
from .common import PositionSchema
from .skeleton import (
    RoomSkeletonSchema,
    CorridorConnectionSchema,
    CorridorSchema,
    MapSkeletonSchema
)
from .detail import (
    RoomSchema,
    MapObjectSchema,
    MapOutputSchema
)

__all__ = [
    # Common
    "PositionSchema",
    # Skeleton
    "RoomSkeletonSchema",
    "CorridorConnectionSchema",
    "CorridorSchema",
    "MapSkeletonSchema",
    # Detail
    "RoomSchema",
    "MapObjectSchema",
    "MapOutputSchema",
]
