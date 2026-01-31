"""
Map Position Calculator

This module calculates the bottom-left (x, y) coordinates for map elements
(rooms and corridors) based on their connections.

Algorithm Overview:
==================

1. INPUT: MapOutputSchema containing:
   - rooms: List of rooms with id, name, width, height
   - corridors: List of corridors with connections (room_id, direction)
   - obj: List of objects (clues, suspects) with relative positions within rooms

2. GRAPH CONSTRUCTION:
   - Build adjacency list from corridor connections
   - Each corridor connects 2+ rooms with directional information
   - Example: Corridor connects Room1(south) <-> Room2(north)
     means Room2 is to the NORTH of Room1

3. BFS ROOM PLACEMENT:
   - Start from first room at center position (0, 0)
   - For each connected room, calculate position based on direction:
     - NORTH: new_y = current_y + current_height/2 + new_height/2 + corridor_length
     - SOUTH: new_y = current_y - current_height/2 - new_height/2 - corridor_length
     - EAST:  new_x = current_x + current_width/2 + new_width/2 + corridor_length
     - WEST:  new_x = current_x - current_width/2 - new_width/2 - corridor_length

4. NORMALIZATION:
   - Find minimum x and y coordinates
   - Shift all positions so minimum becomes 0 (all coordinates positive)

5. OUTPUT:
   - Convert center positions to bottom-left coordinates
   - Return MapPositionResult with all element positions

Visual Example:
==============

    Input corridors:
    - Corridor1: Room1(south) <-> Room2(north)  # Room2 is north of Room1
    - Corridor2: Room1(east) <-> Room3(west)    # Room3 is east of Room1

    Result layout:
                    ┌─────────┐
                    │  Room2  │
                    │  (0,22) │
                    └────┬────┘
                         │ Corridor1
                    ┌────┴────┐      ┌─────────┐
                    │  Room1  │──────│  Room3  │
                    │  (0,0)  │ C2   │  (22,0) │
                    └─────────┘      └─────────┘

    Bottom-left (x,y) coordinates are stored for each element.
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque

from app.models.schemas.map import MapOutputSchema, RoomSchema, CorridorSchema


@dataclass
class MapElementPosition:
    """Position and dimensions of a map element.

    Attributes:
        id: Original element ID from MapOutputSchema
        type: 'room' or 'corridor'
        name: Element name
        x: Bottom-left X coordinate (grid units)
        y: Bottom-left Y coordinate (grid units)
        width: Element width
        height: Element height
        extra_data: Additional data (mood for rooms, connections for corridors)
    """
    id: int
    type: str
    name: str
    x: int
    y: int
    width: int
    height: int
    extra_data: dict


@dataclass
class MapPositionResult:
    """Result of map position calculation.

    Attributes:
        elements: List of all positioned elements (rooms + corridors)
        room_positions: Quick lookup dict of room_id -> (x, y) bottom-left position
    """
    elements: List[MapElementPosition]
    room_positions: Dict[int, Tuple[int, int]]


def calculate_map_positions(
    map_data: MapOutputSchema,
    gap: int = 2
) -> MapPositionResult:
    """
    Calculate bottom-left (x, y) coordinates for all map elements.

    Uses BFS graph traversal based on corridor connections to place rooms,
    then calculates corridor positions between connected rooms.

    Args:
        map_data: MapOutputSchema containing rooms, corridors, and objects
        gap: Spacing between adjacent elements (default: 2)

    Returns:
        MapPositionResult with calculated positions for all elements

    Example:
        >>> from app.models.schemas.map import MapOutputSchema
        >>> map_data = MapOutputSchema(rooms=[...], corridors=[...], obj=[...])
        >>> result = calculate_map_positions(map_data)
        >>> for elem in result.elements:
        ...     print(f"{elem.name}: ({elem.x}, {elem.y})")
    """
    rooms = {r.id: r for r in map_data.rooms}
    corridors = map_data.corridors

    # Step 1: Build adjacency map from corridors
    # room_neighbors[room_id] = [(neighbor_id, direction, corridor), ...]
    room_neighbors: Dict[int, List[Tuple[int, str, CorridorSchema]]] = {
        r.id: [] for r in map_data.rooms
    }

    for corridor in corridors:
        for i, conn in enumerate(corridor.connections):
            for j, other_conn in enumerate(corridor.connections):
                if i != j:
                    # conn.room_id is connected to other_conn.room_id
                    # other_conn.direction tells us WHERE other_conn.room_id is
                    room_neighbors[conn.room_id].append(
                        (other_conn.room_id, other_conn.direction, corridor)
                    )

    # Step 2: Place rooms using BFS (center positions first)
    room_positions: Dict[int, Tuple[int, int]] = {}  # room_id -> (center_x, center_y)

    if not rooms:
        return MapPositionResult(elements=[], room_positions={})

    # Start from first room at origin (center = 0, 0)
    start_room_id = map_data.rooms[0].id
    room_positions[start_room_id] = (0, 0)

    visited = {start_room_id}
    queue = deque([start_room_id])

    while queue:
        current_id = queue.popleft()
        current_room = rooms[current_id]
        cx, cy = room_positions[current_id]

        for neighbor_id, direction, corridor in room_neighbors[current_id]:
            if neighbor_id in visited:
                continue

            neighbor_room = rooms[neighbor_id]

            # Calculate neighbor CENTER position based on direction
            nx, ny = _calculate_neighbor_position(
                cx, cy,
                current_room.width, current_room.height,
                neighbor_room.width, neighbor_room.height,
                direction,
                corridor.width_hint if hasattr(corridor, 'width_hint') else 3,
                corridor.length_hint if hasattr(corridor, 'length_hint') else 5,
                gap
            )

            room_positions[neighbor_id] = (nx, ny)
            visited.add(neighbor_id)
            queue.append(neighbor_id)

    # Step 3: Normalize - shift all positions to positive space
    min_x = min(pos[0] - rooms[rid].width // 2 for rid, pos in room_positions.items())
    min_y = min(pos[1] - rooms[rid].height // 2 for rid, pos in room_positions.items())

    shift_x = -min_x if min_x < 0 else 0
    shift_y = -min_y if min_y < 0 else 0

    # Step 4: Build final element list with bottom-left coordinates
    elements: List[MapElementPosition] = []

    # Add rooms (convert center -> bottom-left)
    for room in map_data.rooms:
        if room.id in room_positions:
            cx, cy = room_positions[room.id]
            # Bottom-left = center - half_dimension
            x = cx - room.width // 2 + shift_x
            y = cy - room.height // 2 + shift_y

            elements.append(MapElementPosition(
                id=room.id,
                type="room",
                name=room.name,
                x=x,
                y=y,
                width=room.width,
                height=room.height,
                extra_data={"mood": room.mood}
            ))

    # Add corridors
    for corridor in corridors:
        pos = _calculate_corridor_position(corridor, room_positions, rooms, shift_x, shift_y)
        if pos:
            elements.append(MapElementPosition(
                id=corridor.id,
                type="corridor",
                name=corridor.name,
                x=pos[0],
                y=pos[1],
                width=pos[2],
                height=pos[3],
                extra_data={
                    "connections": [
                        {"room_id": c.room_id, "direction": c.direction}
                        for c in corridor.connections
                    ]
                }
            ))

    # Build final room_positions with bottom-left coordinates
    final_room_positions = {}
    for room in map_data.rooms:
        if room.id in room_positions:
            cx, cy = room_positions[room.id]
            x = cx - room.width // 2 + shift_x
            y = cy - room.height // 2 + shift_y
            final_room_positions[room.id] = (x, y)

    return MapPositionResult(
        elements=elements,
        room_positions=final_room_positions
    )


def _calculate_neighbor_position(
    cx: int, cy: int,
    cw: int, ch: int,
    nw: int, nh: int,
    direction: str,
    corridor_width: int,
    corridor_length: int,
    gap: int
) -> Tuple[int, int]:
    """
    Calculate neighbor room CENTER position based on connection direction.

    The direction indicates WHERE the neighbor room is relative to current room.

    Visual:
        direction="north" means neighbor is ABOVE current room

             ┌──────────┐
             │ neighbor │  <- placed here (north)
             └────┬─────┘
                  │ corridor
             ┌────┴─────┐
             │ current  │
             └──────────┘

    Args:
        cx, cy: Current room center position
        cw, ch: Current room width/height
        nw, nh: Neighbor room width/height
        direction: 'north', 'south', 'east', 'west'
        corridor_length: Length of connecting corridor
        gap: Additional spacing

    Returns:
        (nx, ny): Neighbor room CENTER position
    """
    offset = corridor_length + gap

    if direction == "north":
        # Neighbor is above: same x, higher y
        return (cx, cy + ch // 2 + nh // 2 + offset)
    elif direction == "south":
        # Neighbor is below: same x, lower y
        return (cx, cy - ch // 2 - nh // 2 - offset)
    elif direction == "east":
        # Neighbor is to the right: higher x, same y
        return (cx + cw // 2 + nw // 2 + offset, cy)
    elif direction == "west":
        # Neighbor is to the left: lower x, same y
        return (cx - cw // 2 - nw // 2 - offset, cy)
    else:
        # Fallback: place to the right
        return (cx + cw + nw + offset, cy)


def _calculate_corridor_position(
    corridor: CorridorSchema,
    room_positions: Dict[int, Tuple[int, int]],
    rooms: Dict[int, RoomSchema],
    shift_x: int,
    shift_y: int
) -> Optional[Tuple[int, int, int, int]]:
    """
    Calculate corridor bottom-left position based on connected rooms.

    The corridor is placed in the gap between two rooms.

    Returns:
        (x, y, width, height) or None if cannot calculate
    """
    if len(corridor.connections) < 2:
        return None

    conn1, conn2 = corridor.connections[0], corridor.connections[1]

    if conn1.room_id not in room_positions or conn2.room_id not in room_positions:
        return None

    r1_cx, r1_cy = room_positions[conn1.room_id]
    r2_cx, r2_cy = room_positions[conn2.room_id]

    room1 = rooms[conn1.room_id]
    room2 = rooms[conn2.room_id]

    # Determine corridor orientation
    dx = abs(r2_cx - r1_cx)
    dy = abs(r2_cy - r1_cy)

    if dx > dy:
        # Horizontal corridor (rooms are side by side)
        min_x = min(r1_cx + room1.width // 2, r2_cx + room2.width // 2)
        max_x = max(r1_cx - room1.width // 2, r2_cx - room2.width // 2)
        mid_y = (r1_cy + r2_cy) // 2

        width = max_x - min_x
        height = corridor.width_hint

        x = min_x + shift_x
        y = mid_y - height // 2 + shift_y
    else:
        # Vertical corridor (rooms are above/below)
        mid_x = (r1_cx + r2_cx) // 2
        min_y = min(r1_cy + room1.height // 2, r2_cy + room2.height // 2)
        max_y = max(r1_cy - room1.height // 2, r2_cy - room2.height // 2)

        width = corridor.width_hint
        height = max_y - min_y

        x = mid_x - width // 2 + shift_x
        y = min_y + shift_y

    # Ensure positive dimensions
    width = max(width, corridor.width_hint)
    height = max(height, corridor.width_hint)

    return (x, y, width, height)
