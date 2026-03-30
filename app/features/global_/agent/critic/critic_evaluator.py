"""Unified Critic AI evaluator — 3 perspectives in a single LLM call."""
import json
import logging

from app.core.utils import extract_json, safe_json_load
from app.models.schemas.critic import (
    CriticType,
    CriticEvaluation,
    UnifiedCriticOutput,
    AggregatedCriticResult,
)
from app.features.global_.llm.llm_client import LLMClient
from app.features.global_.prompt.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class UnifiedCritic:
    """Evaluates a scenario expansion from all 3 perspectives in one LLM call.

    Replaces the previous 3-class design (LogicianCritic, DetectiveCritic,
    DirectorCritic) that required 3 concurrent LLM calls.
    Token savings: ~66% reduction in input tokens (scenario sent once, not 3x).
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load("app/prompts/critic/unified.txt")

    def evaluate(self, scenario_json: dict, iteration: int = 1) -> AggregatedCriticResult:
        """Evaluate a scenario from all 3 critic perspectives.

        Parameters
        ----------
        scenario_json : dict
            The complete scenario data to evaluate.
        iteration : int
            Current iteration number for the aggregated result.

        Returns
        -------
        AggregatedCriticResult
            Aggregated evaluation with all 3 perspectives.
        """
        user_input = json.dumps(scenario_json, indent=2, ensure_ascii=False)

        logger.info("[UnifiedCritic] Starting 3-perspective evaluation...")

        raw_response = self.llm.complete(
            system=self.system_prompt,
            user=user_input,
            response_schema=UnifiedCriticOutput.model_json_schema(),
        )

        json_text = extract_json(raw_response)
        data_dict = safe_json_load(json_text)
        unified = UnifiedCriticOutput.model_validate(data_dict)

        # Log results per perspective
        for name, ev in [
            ("logician", unified.logician),
            ("detective", unified.detective),
            ("director", unified.director),
        ]:
            logger.info(f"[UnifiedCritic/{name}] {ev.status}")

        return unified.to_aggregated(iteration)


# ---------- Legacy aliases for backward compatibility ----------
# These are kept so that any code importing these names won't break.
# They all delegate to the unified prompt internally.

class CriticEvaluator:
    """Legacy base class — kept for backward compatibility only."""
    critic_type: CriticType
    prompt_path: str

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client


class LogicianCritic(CriticEvaluator):
    """Legacy — use UnifiedCritic instead."""
    critic_type = CriticType.LOGICIAN
    prompt_path = "app/prompts/critic/logician.txt"


class DetectiveCritic(CriticEvaluator):
    """Legacy — use UnifiedCritic instead."""
    critic_type = CriticType.DETECTIVE
    prompt_path = "app/prompts/critic/detective.txt"


class DirectorCritic(CriticEvaluator):
    """Legacy — use UnifiedCritic instead."""
    critic_type = CriticType.DIRECTOR
    prompt_path = "app/prompts/critic/director.txt"
