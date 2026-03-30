import logging
from typing import Dict, Tuple

from app.features.global_.prompt.prompt_loader import PromptLoader
from app.features.global_.agent.base_generator import BaseGenerator
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema
from app.models.schemas.map import MapOutputSchema, MapSkeletonSchema, RoomFurnitureSchema
from app.models.schemas.map.skeleton import CorridorSchema, RoomSkeletonSchema

logger = logging.getLogger(__name__)


class MapGenerator(BaseGenerator):
    """Map 생성기 - Skeleton → Furniture → Detail 3단계"""

    def __init__(self, llm_client):
        self.skeleton_prompt = PromptLoader.load("app/prompts/map/skeleton.txt")
        self.detail_prompt = PromptLoader.load("app/prompts/map/detail.txt")
        self.furniture_prompt = PromptLoader.load("app/prompts/furniture/build.txt")
        super().__init__(llm_client, self.skeleton_prompt)

    def generate_skeleton(self, scenario: ScenarioExpansion) -> MapSkeletonSchema:
        """1단계: 방 구조 + 복도 + 위치 관계 생성 → 좌표 보정"""
        skeleton_input = self._extract_skeleton_input(scenario)
        skeleton = self._generate(
            skeleton_input,
            MapSkeletonSchema,
            system_prompt=self.skeleton_prompt,
        )
        return self._fix_corridor_connectivity(skeleton)

    def generate_furniture(
        self,
        scenario: ScenarioExpansion,
        skeleton: MapSkeletonSchema,
    ) -> RoomFurnitureSchema:
        """2단계: 각 방에 가구 3개씩 생성 (skeleton만 필요)"""
        furniture_input = self._extract_furniture_input(scenario, skeleton)
        return self._generate(
            furniture_input,
            RoomFurnitureSchema,
            system_prompt=self.furniture_prompt,
        )

    def generate_detail(
        self,
        scenario: ScenarioExpansion,
        skeleton: MapSkeletonSchema,
        clues: ClueSetSchema,
        furniture: RoomFurnitureSchema,
    ) -> MapOutputSchema:
        """3단계: 오브젝트 배치 — 가구 위치를 피해서 단서·용의자 배치"""
        detail_input = self._extract_detail_input(scenario, skeleton, clues, furniture)
        return self._generate(
            detail_input,
            MapOutputSchema,
            system_prompt=self.detail_prompt,
        )

    def _extract_skeleton_input(self,
                                scenario: ScenarioExpansion) -> dict:
        """Skeleton 생성을 위한 입력 추출"""
        visibility_rules = scenario.world_detail.visibility_rules or []
        access_rules = scenario.world_detail.access_rules or []
        return {
            "meta": scenario.meta.model_dump(mode='json'),
            "incident": scenario.incident.model_dump(mode='json'),
            "world": {
                "locations": scenario.world_detail.locations,
                "visibility_rules": [x.model_dump(mode='json') for x in visibility_rules],
                "access_rules": [x.model_dump(mode='json') for x in access_rules],
                "time_granularity_minutes": scenario.world.time_granularity_minutes,
            },
        }

    def _extract_detail_input(
        self,
        scenario: ScenarioExpansion,
        skeleton: MapSkeletonSchema,
        clues: ClueSetSchema,
        furniture: RoomFurnitureSchema,
    ) -> dict:
        """Detail 생성을 위한 입력 추출 (가구 위치 포함)"""
        return {
            "meta": scenario.meta.model_dump(mode='json'),
            "map_skeleton": skeleton.model_dump(mode='json'),
            "clues": {
                "clues": [
                    c.model_dump(mode='json', include={'id', 'name', 'found_at', 'is_red_herring'})
                    for c in clues.clues
                ]
            },
            "furniture": [
                f.model_dump(mode='json', include={'room_id', 'origin_x', 'origin_y', 'width', 'height', 'name'})
                for f in furniture.furniture
            ],
            "generation_targets": scenario.generation_targets.model_dump(mode='json'),
        }

    # Furniture 생성에 필요한 함수
    def _extract_furniture_input(
        self,
        scenario: ScenarioExpansion,
        skeleton: MapSkeletonSchema,
    ) -> dict:
        """Furniture 생성을 위한 입력 추출 (x, y 제외 — 가구 배치는 방 내부 상대좌표)"""
        return {
            "meta": scenario.meta.model_dump(mode='json'),
            "incident": scenario.incident.model_dump(mode='json', include={'summary', 'location'}),
            "rooms": [
                r.model_dump(mode='json', include={'id', 'name', 'width', 'height', 'mood'})
                for r in skeleton.rooms
            ],
        }

    # ── Corridor connectivity post-processing ──────────────────────────
    '''
    맵을 llm이 만들다보니 후처리를 통해 정상적인 좌표를 가지도록 합니다.
    '''

    def _fix_corridor_connectivity(
        self, skeleton: MapSkeletonSchema
    ) -> MapSkeletonSchema:
        """LLM이 생성한 복도 좌표를 방 경계에 정확히 맞춤 (off-by-one 보정)."""
        room_map: Dict[int, RoomSkeletonSchema] = {r.id: r for r in skeleton.rooms}
        fixed_corridors = []

        for corridor in skeleton.corridors:
            fixed = self._snap_corridor_to_rooms(corridor, room_map)
            fixed_corridors.append(fixed)

        fixed_corridors = self._fix_corridor_junctions(fixed_corridors)

        return MapSkeletonSchema(rooms=skeleton.rooms, corridors=fixed_corridors)

    def _snap_corridor_to_rooms(
        self,
        corridor: CorridorSchema,
        room_map: Dict[int, RoomSkeletonSchema],
    ) -> CorridorSchema:
        """Pass 1: 각 복도를 연결된 방 경계에 스냅."""
        if not corridor.connections:
            return corridor

        h_dirs = {"east", "west"}
        v_dirs = {"north", "south"}

        # Classify connections by axis
        h_conns = [(c, room_map[c.room_id]) for c in corridor.connections
                    if c.direction in h_dirs and c.room_id in room_map]
        v_conns = [(c, room_map[c.room_id]) for c in corridor.connections
                    if c.direction in v_dirs and c.room_id in room_map]

        cx, cy = corridor.x, corridor.y
        cw, ch = corridor.width, corridor.height

        # ── Horizontal axis (east/west connections set x and width) ──
        if len(h_conns) >= 2:
            # Two horizontal endpoints → recompute x and width
            left_x, right_x = self._resolve_h_endpoints(h_conns, corridor)
            cx = left_x
            cw = max(right_x - left_x, 1)
            # Center on y using overlapping range of connected rooms
            cy = self._center_on_perpendicular(
                [room for _, room in h_conns], cy, ch, axis="y"
            )
        elif len(h_conns) == 1:
            conn, room = h_conns[0]
            cx, cw = self._snap_single_h(conn.direction, room, cx, cw)

        # ── Vertical axis (north/south connections set y and height) ──
        if len(v_conns) >= 2:
            bottom_y, top_y = self._resolve_v_endpoints(v_conns, corridor)
            cy = bottom_y
            ch = max(top_y - bottom_y, 1)
            cx = self._center_on_perpendicular(
                [room for _, room in v_conns], cx, cw, axis="x"
            )
        elif len(v_conns) == 1:
            conn, room = v_conns[0]
            cy, ch = self._snap_single_v(conn.direction, room, cy, ch)

        updates = {"x": cx, "y": cy, "width": max(cw, 1), "height": max(ch, 1)}
        return corridor.model_copy(update=updates)

    @staticmethod
    def _snap_single_h(direction: str, room: RoomSkeletonSchema,
                       cx: int, cw: int) -> Tuple[int, int]:
        """Snap one horizontal edge of corridor to room boundary."""
        if direction == "east":
            # Corridor is east of room → corridor left = room right
            cx = room.x + room.width
        else:  # west
            # Corridor is west of room → corridor right = room left
            cx = room.x - cw
        return cx, cw

    @staticmethod
    def _snap_single_v(direction: str, room: RoomSkeletonSchema,
                       cy: int, ch: int) -> Tuple[int, int]:
        """Snap one vertical edge of corridor to room boundary."""
        if direction == "north":
            # Corridor is north of room → corridor bottom = room top
            cy = room.y + room.height
        else:  # south
            # Corridor is south of room → corridor top = room bottom
            cy = room.y - ch
        return cy, ch

    @staticmethod
    def _resolve_h_endpoints(h_conns, corridor) -> Tuple[int, int]:
        """For ≥2 horizontal connections, find left_x and right_x."""
        left_x = corridor.x
        right_x = corridor.x + corridor.width
        for conn, room in h_conns:
            if conn.direction == "east":
                # Corridor left = room right
                left_x = room.x + room.width
            elif conn.direction == "west":
                # Corridor right = room left
                right_x = room.x
        return left_x, right_x

    @staticmethod
    def _resolve_v_endpoints(v_conns, corridor) -> Tuple[int, int]:
        """For ≥2 vertical connections, find bottom_y and top_y."""
        bottom_y = corridor.y
        top_y = corridor.y + corridor.height
        for conn, room in v_conns:
            if conn.direction == "north":
                bottom_y = room.y + room.height
            elif conn.direction == "south":
                top_y = room.y
        return bottom_y, top_y

    @staticmethod
    def _center_on_perpendicular(rooms, current_pos: int, size: int,
                                  axis: str) -> int:
        """Center corridor on the overlapping range of connected rooms."""
        if axis == "y":
            lo = max(r.y for r in rooms)
            hi = min(r.y + r.height for r in rooms)
        else:
            lo = max(r.x for r in rooms)
            hi = min(r.x + r.width for r in rooms)

        if hi > lo:
            return lo + (hi - lo - size) // 2
        return current_pos

    @staticmethod
    def _fix_corridor_junctions(
        corridors: list[CorridorSchema],
    ) -> list[CorridorSchema]:
        """Pass 2: 수직·수평 복도 쌍의 L자 교차점에서 1타일 겹침 보장."""
        TOLERANCE = 3

        def is_horizontal(c: CorridorSchema) -> bool:
            return c.width >= c.height

        def rect(c: CorridorSchema):
            return c.x, c.y, c.x + c.width, c.y + c.height

        updated = [c.model_dump() for c in corridors]

        for i in range(len(corridors)):
            for j in range(i + 1, len(corridors)):
                ci, cj = corridors[i], corridors[j]
                if is_horizontal(ci) == is_horizontal(cj):
                    continue  # same orientation, skip

                h, v = (ci, cj) if is_horizontal(ci) else (cj, ci)
                hi, vi = (i, j) if is_horizontal(ci) else (j, i)

                hx1, hy1, hx2, hy2 = rect(h)
                vx1, vy1, vx2, vy2 = rect(v)

                # Check if they're close enough to form an L-junction
                x_gap = max(0, max(hx1, vx1) - min(hx2, vx2))
                y_gap = max(0, max(hy1, vy1) - min(hy2, vy2))

                if x_gap <= TOLERANCE and y_gap <= TOLERANCE:
                    # Extend horizontal corridor to overlap vertical corridor's x-range
                    new_hx1 = min(hx1, vx1)
                    new_hx2 = max(hx2, vx2)
                    updated[hi]["x"] = new_hx1
                    updated[hi]["width"] = max(new_hx2 - new_hx1, 1)

                    # Extend vertical corridor to overlap horizontal corridor's y-range
                    new_vy1 = min(vy1, hy1)
                    new_vy2 = max(vy2, hy2)
                    updated[vi]["y"] = new_vy1
                    updated[vi]["height"] = max(new_vy2 - new_vy1, 1)

                    logger.debug(
                        "Fixed L-junction: corridor %d ↔ %d",
                        corridors[i].id, corridors[j].id,
                    )

        return [CorridorSchema.model_validate(d) for d in updated]
