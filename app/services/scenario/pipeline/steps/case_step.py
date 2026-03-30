"""Step 1: Generate a narrative case synopsis from the theme string."""
import time
from typing import Any

from app.services.scenario.pipeline.step import PipelineStep
from app.services.agent.scenario_generator import ScenarioGenerator


class CaseGenerationStep(PipelineStep):
    """Generates a free-form case synopsis from a theme keyword.

    Input state keys
    ----------------
    theme : str
        High-level topic for the mystery (e.g. ``"밀실 방화 사망 사건"``).

    Output state key
    ----------------
    case_state : str
        Narrative prose synopsis produced by the LLM.
    """

    input_keys = ["theme"]
    output_key = "case_state"
    schema_type = None
    use_json_retry = False

    def __init__(self, generator: ScenarioGenerator) -> None:
        self._generator = generator

    def run(self, **kwargs: Any) -> str:
        theme: str = kwargs["theme"]
        result = self._generator.generate_case(theme)
        time.sleep(3)
        return result
