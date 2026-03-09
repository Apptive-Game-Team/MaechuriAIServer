"""Critic AI evaluators that check scenario quality from different perspectives."""
import json
import logging
from typing import Type

from app.core.utils import extract_json, safe_json_load
from app.models.schemas.critic import CriticType, CriticEvaluation
from app.services.llm.llm_client import LLMClient
from app.services.prompt.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class CriticEvaluator:
    """Base class for all Critic AI evaluators.

    Each critic loads its own system prompt and evaluates
    a scenario JSON, returning a structured CriticEvaluation.
    """

    critic_type: CriticType
    prompt_path: str

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load(self.prompt_path)

    def evaluate(self, scenario_json: dict) -> CriticEvaluation:
        """Evaluate a scenario and return structured feedback.

        Parameters
        ----------
        scenario_json : dict
            The complete scenario data to evaluate.

        Returns
        -------
        CriticEvaluation
            Structured evaluation with status, feedback, and targets_to_fix.
        """
        user_input = json.dumps(scenario_json, indent=2, ensure_ascii=False)

        logger.info(f"[{self.critic_type.value}] Starting evaluation...")

        raw_response = self.llm.complete(
            system=self.system_prompt,
            user=user_input,
            response_schema=CriticEvaluation.model_json_schema(),
        )

        json_text = extract_json(raw_response)
        data_dict = safe_json_load(json_text)
        result = CriticEvaluation.model_validate(data_dict)

        logger.info(
            f"[{self.critic_type.value}] Evaluation complete: {result.status}"
        )
        return result


class LogicianCritic(CriticEvaluator):
    """Checks physical, temporal, and spatial contradictions."""
    critic_type = CriticType.LOGICIAN
    prompt_path = "app/prompts/critic/logician.txt"


class DetectiveCritic(CriticEvaluator):
    """Checks solvability, clue sufficiency, and red herring quality."""
    critic_type = CriticType.DETECTIVE
    prompt_path = "app/prompts/critic/detective.txt"


class DirectorCritic(CriticEvaluator):
    """Checks tone consistency, character completeness, and data integrity."""
    critic_type = CriticType.DIRECTOR
    prompt_path = "app/prompts/critic/director.txt"
