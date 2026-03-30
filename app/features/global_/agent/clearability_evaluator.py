"""Evaluates whether a fully generated scenario is clearable within 10 turns."""
import json
import logging

from app.core.utils import extract_json, safe_json_load
from app.models.schemas.scenario.clearability import ClearabilityEvaluation
from app.features.global_.llm.llm_client import LLMClient
from app.features.global_.prompt.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class ClearabilityEvaluator:
    """Calls the LLM to judge if a scenario can be solved in 10 turns."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load(
            "app/prompts/scenario/clearability.txt"
        )

    def evaluate(self, scenario_data: dict) -> ClearabilityEvaluation:
        """Evaluate clearability of a complete scenario.

        Parameters
        ----------
        scenario_data : dict
            Full scenario dict containing ground_truth_detail, suspects, and clues.

        Returns
        -------
        ClearabilityEvaluation
            Result with is_clearable flag and reason.
        """
        user_input = json.dumps(scenario_data, indent=2, ensure_ascii=False)

        logger.info("Starting clearability evaluation...")

        raw_response = self.llm.complete(
            system=self.system_prompt,
            user=user_input,
            response_schema=ClearabilityEvaluation.model_json_schema(),
        )

        json_text = extract_json(raw_response)
        data_dict = safe_json_load(json_text)
        result = ClearabilityEvaluation.model_validate(data_dict)

        logger.info(f"Clearability evaluation: is_clearable={result.is_clearable}")
        return result
