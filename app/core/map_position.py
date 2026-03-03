"""
Map Position Calculator - Validates and normalizes LLM-generated coordinates.

Since the LLM now generates `x`, `y`, `width`, and `height` directly in the MapSkeletonSchema,
this module simply converts those coordinates into the MapPositionResult format,
ensuring all coordinates are positive by shifting them if necessary.
"""
from typing import Dict, List, Tuple
from dataclasses import dataclass

from app.models.schemas.map import MapOutputSchema, MapElementType


@dataclass
class MapElementPosition:
    """Position and dimensions of a map element."""
    id: int
    type: MapElementType
    name: str
    x: int
    y: int
    width: int
    height: int


@dataclass
class MapPositionResult:
    """Result containing positioned elements and room position lookup."""
    elements: List[MapElementPosition]
    room_positions: Dict[int, Tuple[int, int]]


def calculate_map_positions(map_data: MapOutputSchema, gap: int = 1) -> MapPositionResult:
    """
    Validates and normalizes the absolute coordinates provided by the LLM.
    Shifts all coordinates so the minimum x and y are 0.
    """
    if not map_data.rooms:
        return MapPositionResult(elements=[], room_positions={})

    # Find the minimum x and y to normalize to positive space
    min_x = float('inf')
    min_y = float('inf')

    # Note: Using getattr to handle potential transition cases where older models 
    # might not have generated x/y yet. Defaults to 0 if missing.
    for room in map_data.rooms:
        min_x = min(min_x, getattr(room, 'x', 0))
        min_y = min(min_y, getattr(room, 'y', 0))

    for corr in map_data.corridors:
        min_x = min(min_x, getattr(corr, 'x', 0))
        min_y = min(min_y, getattr(corr, 'y', 0))

    # If everything is already positive, shift is 0
    shift_x = -min_x if min_x < 0 else 0
    shift_y = -min_y if min_y < 0 else 0

    elements = []
    room_positions = {}

    # Process Rooms
    for room in map_data.rooms:
        rx = getattr(room, 'x', 0) + shift_x
        ry = getattr(room, 'y', 0) + shift_y
        elements.append(MapElementPosition(
            id=room.id,
            type="room",
            name=room.name,
            x=rx,
            y=ry,
            width=room.width,
            height=room.height
        ))
        room_positions[room.id] = (rx, ry)

    # Process Corridors
    for corr in map_data.corridors:
        cx = getattr(corr, 'x', 0) + shift_x
        cy = getattr(corr, 'y', 0) + shift_y
        cw = getattr(corr, 'width', corr.width_hint)
        ch = getattr(corr, 'height', corr.length_hint)
        
        elements.append(MapElementPosition(
            id=corr.id,
            type="corridor",
            name=corr.name,
            x=cx,
            y=cy,
            width=cw,
            height=ch
        ))

    return MapPositionResult(
        elements=elements,
        room_positions=room_positions
    )
