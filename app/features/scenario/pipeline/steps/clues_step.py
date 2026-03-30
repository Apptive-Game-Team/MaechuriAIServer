"""Step 6: Generate evidence clues from expansion + map skeleton."""
from typing import Any

from app.models.schemas.clue.response import ClueSetSchema
from app.models.schemas.map.skeleton import MapSkeletonSchema
from app.models.schemas.scenario import ScenarioExpansion
from app.features.scenario.pipeline.step import PipelineStep
from app.features.global_.agent.clue_generator import ClueGenerator


class ClueGenerationStep(PipelineStep):
    """Generates all evidence clues for the scenario.

    Input state keys
    ----------------
    expansion : ScenarioExpansion
        Approved expansion supplying case/world/ground truth context.
    map_skeleton : MapSkeletonSchema
        Room layout for location-aware clue placement.
    clearability_feedback : str
        Empty string on the first attempt; set to evaluator feedback when
        retrying after a failed clearability check.

    Output state key
    ----------------
    clues : ClueSetSchema
        Full set of evidence clues with logic explanations and red-herring
        flags.
    """

    input_keys = ["expansion", "map_skeleton", "clearability_feedback"]
    output_key = "clues"
    schema_type = ClueSetSchema

    def __init__(self, generator: ClueGenerator) -> None:
        self._generator = generator
        self._max_output_tokens: int | None = None

    def run(self, **kwargs: Any) -> ClueSetSchema:
        expansion: ScenarioExpansion = kwargs["expansion"]
        map_skeleton: MapSkeletonSchema = kwargs["map_skeleton"]
        clearability_feedback: str = kwargs.get("clearability_feedback", "")

        return self._generator.generate_clues(
            expansion,
            map_skeleton,
            clearability_feedback=clearability_feedback,
        )
