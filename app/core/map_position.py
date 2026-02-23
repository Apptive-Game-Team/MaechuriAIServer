"""
Map Position Calculator - Calculates (x, y) coordinates for map elements.

Algorithm: BFS traversal from first room, placing neighbors based on corridor directions.
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque

from app.models.schemas.map import MapOutputSchema, RoomSkeletonSchema, CorridorSchema, MapElementType


# Direction vectors: (x_multiplier, y_multiplier, use_width_for_current, use_width_for_neighbor)
DIRECTION_VECTORS = {
    "north": (0, 1, False, False),   # Same x, higher y (use heights)
    "south": (0, -1, False, False),  # Same x, lower y (use heights)
    "east": (1, 0, True, True),      # Higher x, same y (use widths)
    "west": (-1, 0, True, True),     # Lower x, same y (use widths)
}


@dataclass
class MapElementPosition:
    """Position and dimensions of a map element."""
    id: int
    type: MapElementType
    name: str
    x: int     # Bottom-left X
    y: int     # Bottom-left Y
    width: int
    height: int


@dataclass
class MapPositionResult:
    """Result containing positioned elements and room position lookup."""
    elements: List[MapElementPosition]
    room_positions: Dict[int, Tuple[int, int]]


def calculate_map_positions(map_data: MapOutputSchema, gap: int = 2) -> MapPositionResult:
    """Calculate bottom-left coordinates for all map elements using BFS."""
    if not map_data.rooms:
        return MapPositionResult(elements=[], room_positions={})

    rooms = {r.id: r for r in map_data.rooms}

    # Build adjacency: room_id -> [(neighbor_id, direction, corridor), ...]
    neighbors = {r.id: [] for r in map_data.rooms}
    for corridor in map_data.corridors:
        for i, conn in enumerate(corridor.connections):
            for j, other in enumerate(corridor.connections):
                if i != j:
                    neighbors[conn.room_id].append((other.room_id, other.direction, corridor))

    # BFS to place rooms (center positions)
    centers = {map_data.rooms[0].id: (0, 0)}
    queue = deque([map_data.rooms[0].id])
    visited = {map_data.rooms[0].id}

    while queue:
        curr_id = queue.popleft()
        curr = rooms[curr_id]
        cx, cy = centers[curr_id]

        for nbr_id, direction, corridor in neighbors[curr_id]:
            if nbr_id in visited:
                continue
            nbr = rooms[nbr_id]
            length = getattr(corridor, 'length_hint', 5)
            centers[nbr_id] = _calc_neighbor_pos(cx, cy, curr, nbr, direction, length + gap)
            visited.add(nbr_id)
            queue.append(nbr_id)

    # Normalize to positive space
    shift_x = -min(cx - rooms[rid].width // 2 for rid, (cx, _) in centers.items())
    shift_y = -min(cy - rooms[rid].height // 2 for rid, (_, cy) in centers.items())
    shift_x = max(0, shift_x)
    shift_y = max(0, shift_y)

    # Helper: center -> bottom-left
    def to_bottom_left(room_id: int) -> Tuple[int, int]:
        cx, cy = centers[room_id]
        r = rooms[room_id]
        return cx - r.width // 2 + shift_x, cy - r.height // 2 + shift_y

    # Build elements
    elements = [
        MapElementPosition(
            id=r.id, type="room", name=r.name,
            x=to_bottom_left(r.id)[0], y=to_bottom_left(r.id)[1],
            width=r.width, height=r.height
        )
        for r in map_data.rooms if r.id in centers
    ]

    for corridor in map_data.corridors:
        pos = _calc_corridor_pos(corridor, centers, rooms, shift_x, shift_y)
        if pos:
            elements.append(MapElementPosition(
                id=corridor.id, type="corridor", name=corridor.name,
                x=pos[0], y=pos[1], width=pos[2], height=pos[3]
            ))

    return MapPositionResult(
        elements=elements,
        room_positions={r.id: to_bottom_left(r.id) for r in map_data.rooms if r.id in centers}
    )


def _calc_neighbor_pos(
    cx: int, cy: int, curr: RoomSkeletonSchema, nbr: RoomSkeletonSchema, direction: str, offset: int
) -> Tuple[int, int]:
    """Calculate neighbor center position based on direction."""
    vec = DIRECTION_VECTORS.get(direction, (1, 0, True, True))
    x_mult, y_mult, use_w_curr, use_w_nbr = vec

    curr_half = (curr.width if use_w_curr else curr.height) // 2
    nbr_half = (nbr.width if use_w_nbr else nbr.height) // 2

    return (
        cx + x_mult * (curr_half + nbr_half + offset),
        cy + y_mult * (curr_half + nbr_half + offset)
    )


def _calc_corridor_pos(
    corridor: CorridorSchema,
    centers: Dict[int, Tuple[int, int]],
    rooms: Dict[int, RoomSkeletonSchema],
    shift_x: int, shift_y: int
) -> Optional[Tuple[int, int, int, int]]:
    """Calculate corridor position between two rooms."""
    if len(corridor.connections) < 2:
        return None

    c1, c2 = corridor.connections[0], corridor.connections[1]
    if c1.room_id not in centers or c2.room_id not in centers:
        return None

    r1_cx, r1_cy = centers[c1.room_id]
    r2_cx, r2_cy = centers[c2.room_id]
    r1, r2 = rooms[c1.room_id], rooms[c2.room_id]

    is_horizontal = abs(r2_cx - r1_cx) > abs(r2_cy - r1_cy)

    if is_horizontal:
        min_x = min(r1_cx + r1.width // 2, r2_cx + r2.width // 2)
        max_x = max(r1_cx - r1.width // 2, r2_cx - r2.width // 2)
        w, h = max(max_x - min_x, corridor.width_hint), corridor.width_hint
        x, y = min_x + shift_x, (r1_cy + r2_cy) // 2 - h // 2 + shift_y
    else:
        min_y = min(r1_cy + r1.height // 2, r2_cy + r2.height // 2)
        max_y = max(r1_cy - r1.height // 2, r2_cy - r2.height // 2)
        w, h = corridor.width_hint, max(max_y - min_y, corridor.width_hint)
        x, y = (r1_cx + r2_cx) // 2 - w // 2 + shift_x, min_y + shift_y

    return x, y, w, h
