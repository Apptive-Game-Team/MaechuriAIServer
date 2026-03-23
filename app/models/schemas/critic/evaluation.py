"""Pydantic schemas for Critic AI evaluation output."""
from enum import Enum
from typing import ClassVar, Literal, Set
from pydantic import BaseModel, Field, computed_field


class CriticType(str, Enum):
    LOGICIAN = "logician"
    DETECTIVE = "detective"
    DIRECTOR = "director"


class CriticEvaluation(BaseModel):
    """Structured output from a single Critic AI perspective.

    Each perspective must return this exact schema so the aggregator
    can programmatically decide whether refinement is needed.
    """
    status: Literal["Pass", "Fail"] = Field(
        description="'Pass' if the scenario meets this critic's criteria, 'Fail' otherwise."
    )
    feedback: str = Field(
        default="",
        description="Detailed explanation of what is wrong. Empty when status is Pass."
    )
    target_to_fix: list[str] = Field(
        default_factory=list,
        description=(
            "JSON paths / section names the Generator should fix. "
            "e.g. ['ground_truth_detail.crime_method', 'suspects[2].timeline']. "
            "Empty when status is Pass."
        )
    )


class UnifiedCriticOutput(BaseModel):
    """Output from the unified critic — all 3 perspectives in one LLM call."""
    logician: CriticEvaluation = Field(
        description="Physical, temporal, and spatial consistency evaluation"
    )
    detective: CriticEvaluation = Field(
        description="Solvability, clue sufficiency, and fairness evaluation"
    )
    director: CriticEvaluation = Field(
        description="Tone, data completeness, and narrative evaluation"
    )

    def to_aggregated(self, iteration: int) -> "AggregatedCriticResult":
        """Convert to AggregatedCriticResult for backward compatibility."""
        return AggregatedCriticResult(
            iteration=iteration,
            evaluations={
                CriticType.LOGICIAN.value: self.logician,
                CriticType.DETECTIVE.value: self.detective,
                CriticType.DIRECTOR.value: self.director,
            },
        )


class AggregatedCriticResult(BaseModel):
    """Aggregation of all critic evaluations for one refinement iteration."""
    iteration: int = Field(description="Current iteration number (1-based)")
    evaluations: dict[str, CriticEvaluation] = Field(
        description="Mapping of critic_type -> evaluation result"
    )

    @computed_field
    @property
    def all_passed(self) -> bool:
        """True only if every critic returned Pass."""
        return all(ev.status == "Pass" for ev in self.evaluations.values())

    # Skeleton-level fields that, if flagged, mean we need to re-gen skeleton
    SKELETON_FIELDS: ClassVar[Set[str]] = {
        "meta", "incident", "world", "ground_truth",
        "ground_truth.culprit_count", "ground_truth.crime_time_range",
        "ground_truth.crime_location", "incident.summary",
        "world.locations",
    }

    @property
    def requires_skeleton_regen(self) -> bool:
        """True if any target_to_fix points to a skeleton-level field."""
        for ev in self.evaluations.values():
            if ev.status == "Fail":
                for target in ev.target_to_fix:
                    root = target.split(".")[0]
                    if root in self.SKELETON_FIELDS or target in self.SKELETON_FIELDS:
                        return True
        return False

    def build_refinement_feedback(self) -> str:
        """Combine all failed critic feedback into a single refinement prompt."""
        lines: list[str] = []
        for critic_name, evaluation in self.evaluations.items():
            if evaluation.status == "Fail":
                lines.append(f"=== [{critic_name.upper()}] ===")
                lines.append(f"Feedback: {evaluation.feedback}")
                lines.append(f"Targets to fix: {', '.join(evaluation.target_to_fix)}")
                lines.append("")
        return "\n".join(lines)
