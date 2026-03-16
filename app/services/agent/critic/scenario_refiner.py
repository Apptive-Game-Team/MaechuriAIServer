"""Scenario refinement loop orchestrator.

Evaluates ScenarioExpansion with 3 concurrent critics.
On failure, either re-generates expansion or signals skeleton regen.
"""
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.core.utils import extract_json, safe_json_load
from app.models.schemas.critic import (
    CriticEvaluation,
    AggregatedCriticResult,
)
from app.models.schemas.scenario import ScenarioExpansion
from app.services.llm.llm_client import LLMClient
from app.services.prompt.prompt_loader import PromptLoader
from .critic_evaluator import (
    CriticEvaluator,
    LogicianCritic,
    DetectiveCritic,
    DirectorCritic,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class RegenLevel(str, Enum):
    """Which stage to re-generate from."""
    NONE = "none"            # All critics passed
    EXPANSION = "expansion"  # Re-generate expansion only
    SKELETON = "skeleton"    # Go back and re-generate skeleton


@dataclass
class RefinementResult:
    """Result of the critic refinement loop."""
    expansion: Optional[ScenarioExpansion]
    regen_level: RegenLevel
    last_feedback: str  # Last critic feedback (empty if passed)
    evaluation_history: list[AggregatedCriticResult] = field(default_factory=list)


class ScenarioRefiner:
    """Orchestrates critic evaluation on ScenarioExpansion.

    Workflow:
        1. Run 3 critics concurrently on the expansion
        2. All pass → return approved expansion
        3. Failures in skeleton-level fields → signal skeleton regen
        4. Failures in expansion-level fields → refine expansion via LLM
        5. Repeat up to MAX_RETRIES
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.critics: list[CriticEvaluator] = [
            LogicianCritic(llm_client),
            DetectiveCritic(llm_client),
            DirectorCritic(llm_client),
        ]
        self.refinement_prompt = PromptLoader.load(
            "app/prompts/critic/refinement.txt"
        )

    def evaluate_and_refine(
        self, expansion: ScenarioExpansion
    ) -> RefinementResult:
        """Run the critic loop on a ScenarioExpansion.

        Parameters
        ----------
        expansion : ScenarioExpansion
            The expansion to evaluate.

        Returns
        -------
        RefinementResult
            Contains the (possibly refined) expansion and what level
            of regeneration is needed if it still fails.
        """
        expansion_dict = expansion.model_dump(mode="json")
        history: list[AggregatedCriticResult] = []

        for iteration in range(1, MAX_RETRIES + 1):
            logger.info(
                f"=== Critic Evaluation — Iteration {iteration}/{MAX_RETRIES} ==="
            )

            aggregated = self._run_critics(expansion_dict, iteration)
            history.append(aggregated)

            # All passed
            if aggregated.all_passed:
                logger.info(f"All critics passed on iteration {iteration}!")
                return RefinementResult(
                    expansion=ScenarioExpansion.model_validate(expansion_dict),
                    regen_level=RegenLevel.NONE,
                    last_feedback="",
                    evaluation_history=history,
                )

            # Log failures
            for name, ev in aggregated.evaluations.items():
                if ev.status == "Fail":
                    logger.warning(f"[{name}] FAILED: {ev.feedback[:200]}...")

            # If skeleton-level fields need fixing, signal skeleton regen
            if aggregated.requires_skeleton_regen:
                logger.warning(
                    "Critic feedback targets skeleton-level fields. "
                    "Signaling skeleton regeneration."
                )
                return RefinementResult(
                    expansion=None,
                    regen_level=RegenLevel.SKELETON,
                    last_feedback=aggregated.build_refinement_feedback(),
                    evaluation_history=history,
                )

            # Last iteration — no more retries
            if iteration == MAX_RETRIES:
                break

            # Refine expansion via LLM
            expansion_dict = self._refine_expansion(expansion_dict, aggregated)
            time.sleep(3)

        # Exhausted retries — signal expansion regen
        logger.error(
            f"Expansion failed critic evaluation after {MAX_RETRIES} iterations."
        )
        return RefinementResult(
            expansion=None,
            regen_level=RegenLevel.EXPANSION,
            last_feedback=aggregated.build_refinement_feedback(),
            evaluation_history=history,
        )

    def _run_critics(
        self, expansion_dict: dict, iteration: int
    ) -> AggregatedCriticResult:
        """Run all critics concurrently."""
        evaluations: dict[str, CriticEvaluation] = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_critic = {
                executor.submit(critic.evaluate, expansion_dict): critic
                for critic in self.critics
            }

            for future in as_completed(future_to_critic):
                critic = future_to_critic[future]
                critic_name = critic.critic_type.value
                try:
                    result = future.result()
                    evaluations[critic_name] = result
                except Exception as e:
                    logger.error(
                        f"[{critic_name}] evaluation error: {e}"
                    )
                    evaluations[critic_name] = CriticEvaluation(
                        status="Fail",
                        feedback=f"Critic 평가 중 오류 발생: {str(e)}",
                        target_to_fix=[],
                    )

        return AggregatedCriticResult(
            iteration=iteration,
            evaluations=evaluations,
        )

    def _refine_expansion(
        self, expansion_dict: dict, aggregated: AggregatedCriticResult
    ) -> dict:
        """Send failed feedback to the LLM to refine the expansion."""
        feedback_text = aggregated.build_refinement_feedback()

        all_targets: list[str] = []
        for ev in aggregated.evaluations.values():
            if ev.status == "Fail":
                all_targets.extend(ev.target_to_fix)
        unique_targets = list(set(all_targets))

        user_input = json.dumps(
            {
                "original_scenario": expansion_dict,
                "critic_feedback": feedback_text,
                "targets_to_fix": unique_targets,
                "iteration": aggregated.iteration,
            },
            indent=2,
            ensure_ascii=False,
        )

        logger.info(
            f"Refining expansion — fixing {len(unique_targets)} targets: "
            f"{unique_targets[:5]}{'...' if len(unique_targets) > 5 else ''}"
        )

        raw_response = self.llm.complete(
            system=self.refinement_prompt,
            user=user_input,
            response_schema=ScenarioExpansion.model_json_schema(),
        )

        json_text = extract_json(raw_response)
        refined_dict = safe_json_load(json_text)

        # Validate it parses
        ScenarioExpansion.model_validate(refined_dict)

        logger.info("Refinement complete — re-evaluating with critics...")
        return refined_dict
