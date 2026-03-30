"""Step 5: Generate suspects from expansion + map skeleton."""
from typing import Any

from app.models.schemas.suspect import (
    SuspectGenerationRequest,
    SuspectGenerationListSchema,
)
from app.models.schemas.map.skeleton import MapSkeletonSchema
from app.models.schemas.scenario import ScenarioExpansion
from app.services.scenario.pipeline.step import PipelineStep
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.scenario.scenario_generate_helper import inject_sequential_id


class SuspectGenerationStep(PipelineStep):
    """Generates all suspects for the scenario.

    Input state keys
    ----------------
    expansion : ScenarioExpansion
        Approved expansion that supplies world context and ground truth.
    map_skeleton : MapSkeletonSchema
        Room layout used for location-aware suspect placement.
    clearability_feedback : str
        Empty string on the first attempt; set to the evaluator's
        feedback text when retrying after a failed clearability check.

    Output state key
    ----------------
    suspects : SuspectGenerationListSchema
        All generated suspects with facts, personalities, and visual
        descriptions.
    """

    input_keys = ["expansion", "map_skeleton", "clearability_feedback"]
    output_key = "suspects"
    schema_type = SuspectGenerationListSchema

    def __init__(self, generator: SuspectGenerator) -> None:
        self._generator = generator
        self._max_output_tokens: int | None = None

    def run(self, **kwargs: Any) -> SuspectGenerationListSchema:
        expansion: ScenarioExpansion = kwargs["expansion"]
        map_skeleton: MapSkeletonSchema = kwargs["map_skeleton"]
        clearability_feedback: str = kwargs.get("clearability_feedback", "")

        suspect_req = SuspectGenerationRequest.from_expansion(
            expansion, map_skeleton
        )
        result = self._generator.generate(
            suspect_req,
            clearability_feedback=clearability_feedback,
        )
        if result is not None:
            inject_sequential_id(result, "fact_id")
        return result
