"""Step 4: Generate the map skeleton from the scenario expansion."""
from typing import Any

from app.models.schemas.map.skeleton import MapSkeletonSchema
from app.models.schemas.scenario import ScenarioExpansion
from app.services.scenario.pipeline.step import PipelineStep
from app.services.agent.map_generator import MapGenerator


class MapSkeletonStep(PipelineStep):
    """Generates the room/corridor layout skeleton.

    Input state keys
    ----------------
    expansion : ScenarioExpansion
        Approved, fully detailed expansion.

    Output state key
    ----------------
    map_skeleton : MapSkeletonSchema
        Rooms, corridors, and position metadata for the game map.
    """

    input_keys = ["expansion"]
    output_key = "map_skeleton"
    schema_type = MapSkeletonSchema

    def __init__(self, generator: MapGenerator) -> None:
        self._generator = generator
        self._max_output_tokens: int | None = None

    def run(self, **kwargs: Any) -> MapSkeletonSchema:
        expansion: ScenarioExpansion = kwargs["expansion"]
        return self._generator.generate_skeleton(expansion)
