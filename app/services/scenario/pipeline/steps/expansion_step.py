"""Step 3: Expand the scenario skeleton into a full ScenarioExpansion."""
from typing import Any

from app.models.schemas.scenario import ScenarioSkeleton, ScenarioExpansion
from app.services.scenario.pipeline.step import PipelineStep
from app.services.agent.scenario_generator import ScenarioGenerator


class ExpansionGenerationStep(PipelineStep):
    """Expands the skeleton into detailed world context and ground truth.

    Input state keys
    ----------------
    skeleton : ScenarioSkeleton
        Structural outline (output of :class:`SkeletonGenerationStep`).

    Output state key
    ----------------
    expansion : ScenarioExpansion
        Fully detailed scenario including world context, ground truth,
        generation targets, and constraints.
    """

    input_keys = ["skeleton"]
    output_key = "expansion"
    schema_type = ScenarioExpansion

    def __init__(self, generator: ScenarioGenerator) -> None:
        self._generator = generator
        # Exposed so JSONParseRetry can escalate max_output_tokens on retry.
        self._max_output_tokens: int | None = None

    def run(self, **kwargs: Any) -> ScenarioExpansion:
        skeleton: ScenarioSkeleton = kwargs["skeleton"]
        return self._generator.generate_expansion(skeleton)
