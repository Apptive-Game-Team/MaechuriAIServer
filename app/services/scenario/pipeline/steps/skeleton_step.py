"""Step 2: Generate a structured scenario skeleton from the case synopsis."""
from typing import Any

from app.models.schemas.scenario import ScenarioSkeleton
from app.services.scenario.pipeline.step import PipelineStep
from app.services.agent.scenario_generator import ScenarioGenerator


class SkeletonGenerationStep(PipelineStep):
    """Generates the structural skeleton of the scenario.

    Input state keys
    ----------------
    case_state : str
        Narrative case synopsis (output of :class:`CaseGenerationStep`).

    Output state key
    ----------------
    skeleton : ScenarioSkeleton
        Structured skeleton containing meta, incident, world, and
        ground-truth outline.
    """

    input_keys = ["case_state"]
    output_key = "skeleton"
    schema_type = ScenarioSkeleton

    def __init__(self, generator: ScenarioGenerator) -> None:
        self._generator = generator
        # Exposed so JSONParseRetry can escalate max_output_tokens on retry.
        self._max_output_tokens: int | None = None

    def run(self, **kwargs: Any) -> ScenarioSkeleton:
        case_state: str = kwargs["case_state"]
        return self._generator.generate_skeleton(case_state)
