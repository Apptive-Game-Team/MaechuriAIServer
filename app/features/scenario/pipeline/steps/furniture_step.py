"""Step 7: Generate room furniture from expansion + map skeleton."""
from typing import Any

from app.models.schemas.map.detail import RoomFurnitureSchema
from app.models.schemas.map.skeleton import MapSkeletonSchema
from app.models.schemas.scenario import ScenarioExpansion
from app.features.scenario.pipeline.step import PipelineStep
from app.features.global_.agent.map_generator import MapGenerator


class FurnitureGenerationStep(PipelineStep):
    """Generates furniture items for each room in the map.

    This step depends only on the map skeleton (not on clues), so it can
    run in parallel with :class:`SuspectGenerationStep` and
    :class:`ClueGenerationStep` once the map skeleton is available.

    Input state keys
    ----------------
    expansion : ScenarioExpansion
        Scenario context used for thematic furniture selection.
    map_skeleton : MapSkeletonSchema
        Room layout that determines how many furniture slots exist per room.

    Output state key
    ----------------
    furniture : RoomFurnitureSchema
        Per-room furniture lists with positions.
    """

    input_keys = ["expansion", "map_skeleton"]
    output_key = "furniture"
    schema_type = RoomFurnitureSchema

    def __init__(self, generator: MapGenerator) -> None:
        self._generator = generator
        self._max_output_tokens: int | None = None

    def run(self, **kwargs: Any) -> RoomFurnitureSchema:
        expansion: ScenarioExpansion = kwargs["expansion"]
        map_skeleton: MapSkeletonSchema = kwargs["map_skeleton"]
        return self._generator.generate_furniture(expansion, map_skeleton)
