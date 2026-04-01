"""Step 8: Generate map detail — object placement (clues + suspects)."""
from typing import Any

from app.models.schemas.clue.response import ClueSetSchema
from app.models.schemas.map.detail import MapOutputSchema, RoomFurnitureSchema
from app.models.schemas.map.skeleton import MapSkeletonSchema
from app.models.schemas.scenario import ScenarioExpansion
from app.services.scenario.pipeline.step import PipelineStep
from app.services.agent.map_generator import MapGenerator


class MapDetailStep(PipelineStep):
    """Places clues and suspects on the map while respecting furniture.

    This is the final map generation step and depends on clues and
    furniture being ready.

    Input state keys
    ----------------
    expansion : ScenarioExpansion
        Scenario context.
    map_skeleton : MapSkeletonSchema
        Room/corridor layout.
    clues : ClueSetSchema
        Evidence items to be placed on the map.
    furniture : RoomFurnitureSchema
        Existing furniture to avoid when positioning objects.

    Output state key
    ----------------
    map_detail : MapOutputSchema
        Complete map with all object positions.
    """

    input_keys = ["expansion", "map_skeleton", "clues", "furniture"]
    output_key = "map_detail"
    schema_type = MapOutputSchema

    def __init__(self, generator: MapGenerator) -> None:
        self._generator = generator
        self._max_output_tokens: int | None = None

    def run(self, **kwargs: Any) -> MapOutputSchema:
        expansion: ScenarioExpansion = kwargs["expansion"]
        map_skeleton: MapSkeletonSchema = kwargs["map_skeleton"]
        clues: ClueSetSchema = kwargs["clues"]
        furniture: RoomFurnitureSchema = kwargs["furniture"]
        return self._generator.generate_detail(
            expansion, map_skeleton, clues, furniture
        )
