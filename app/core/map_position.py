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

OPPOSITE_DIRECTION = {"north": "south", "south": "north", "east": "west", "west": "east"}


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
                    neighbors[conn.room_id].append((other.room_id, OPPOSITE_DIRECTION[other.direction], corridor))

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

    # Post-BFS overlap correction
    placed_order = list(centers.keys())
    _resolve_overlaps(placed_order, centers, rooms, neighbors, gap)

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
        segments = _calc_corridor_segments(corridor, centers, rooms, shift_x, shift_y)
        for idx, seg in enumerate(segments):
            elements.append(MapElementPosition(
                id=corridor.id, type="corridor", name=corridor.name,
                x=seg[0], y=seg[1], width=seg[2], height=seg[3]
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


def _resolve_overlaps(
    placed_order: List[int],
    centers: Dict[int, Tuple[int, int]],
    rooms: Dict[int, RoomSkeletonSchema],
    neighbors: Dict[int, list],
    gap: int
) -> None:
    """Nudge overlapping rooms along their placement direction until clear."""
    max_iterations = 50
    for _ in range(max_iterations):
        found_overlap = False
        for i in range(len(placed_order)):
            for j in range(i + 1, len(placed_order)):
                rid_a, rid_b = placed_order[i], placed_order[j]
                if _rooms_overlap(centers[rid_a], rooms[rid_a], centers[rid_b], rooms[rid_b], gap):
                    found_overlap = True
                    # Nudge the later-placed room away from the earlier one
                    ax, ay = centers[rid_a]
                    bx, by = centers[rid_b]
                    dx, dy = bx - ax, by - ay
                    if dx == 0 and dy == 0:
                        dx = 1  # arbitrary tiebreak
                    if abs(dx) >= abs(dy):
                        nudge_x = 1 if dx >= 0 else -1
                        nudge_y = 0
                    else:
                        nudge_x = 0
                        nudge_y = 1 if dy >= 0 else -1
                    centers[rid_b] = (bx + nudge_x, by + nudge_y)
        if not found_overlap:
            break


def _rooms_overlap(
    c1: Tuple[int, int], r1: RoomSkeletonSchema,
    c2: Tuple[int, int], r2: RoomSkeletonSchema,
    gap: int
) -> bool:
    """Check AABB overlap between two rooms (with gap margin)."""
    l1 = c1[0] - r1.width // 2 - gap
    r1_right = c1[0] + r1.width // 2 + gap
    b1 = c1[1] - r1.height // 2 - gap
    t1 = c1[1] + r1.height // 2 + gap

    l2 = c2[0] - r2.width // 2
    r2_right = c2[0] + r2.width // 2
    b2 = c2[1] - r2.height // 2
    t2 = c2[1] + r2.height // 2

    return l1 < r2_right and r1_right > l2 and b1 < t2 and t1 > b2


def _calc_corridor_segments(
    corridor: CorridorSchema,
    centers: Dict[int, Tuple[int, int]],
    rooms: Dict[int, RoomSkeletonSchema],
    shift_x: int, shift_y: int
) -> List[Tuple[int, int, int, int]]:
    """Calculate corridor as pairwise segments between each adjacent pair of rooms."""
    valid = [c for c in corridor.connections if c.room_id in centers]
    if len(valid) < 2:
        return []

    # For 2-way corridors, just one segment. For 3+, one segment per pair.
    if len(valid) == 2:
        seg = _corridor_between_two(
            valid[0].room_id, valid[1].room_id,
            corridor.width_hint, centers, rooms, shift_x, shift_y
        )
        return [seg] if seg else []

    # 3+ connections: chain pairwise segments (0↔1, 1↔2, ...)
    segments = []
    for k in range(len(valid) - 1):
        seg = _corridor_between_two(
            valid[k].room_id, valid[k + 1].room_id,
            corridor.width_hint, centers, rooms, shift_x, shift_y
        )
        if seg:
            segments.append(seg)
    return segments


def _corridor_between_two(
    rid1: int, rid2: int, width_hint: int,
    centers: Dict[int, Tuple[int, int]],
    rooms: Dict[int, RoomSkeletonSchema],
    shift_x: int, shift_y: int
) -> Optional[Tuple[int, int, int, int]]:
    """Calculate a single corridor rectangle between two rooms."""
    r1_cx, r1_cy = centers[rid1]
    r2_cx, r2_cy = centers[rid2]
    r1, r2 = rooms[rid1], rooms[rid2]

    is_horizontal = abs(r2_cx - r1_cx) > abs(r2_cy - r1_cy)

    if is_horizontal:
        edge1 = r1_cx + r1.width // 2 if r2_cx > r1_cx else r1_cx - r1.width // 2
        edge2 = r2_cx - r2.width // 2 if r2_cx > r1_cx else r2_cx + r2.width // 2
        left = min(edge1, edge2)
        right = max(edge1, edge2)
        w = max(right - left, width_hint)
        h = width_hint
        x = left + shift_x
        y = (r1_cy + r2_cy) // 2 - h // 2 + shift_y
    else:
        edge1 = r1_cy + r1.height // 2 if r2_cy > r1_cy else r1_cy - r1.height // 2
        edge2 = r2_cy - r2.height // 2 if r2_cy > r1_cy else r2_cy + r2.height // 2
        bottom = min(edge1, edge2)
        top = max(edge1, edge2)
        w = width_hint
        h = max(top - bottom, width_hint)
        x = (r1_cx + r2_cx) // 2 - w // 2 + shift_x
        y = bottom + shift_y

    return x, y, w, h
