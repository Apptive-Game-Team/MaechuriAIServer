"""Scenario-generation feature package.

This package groups every component that belongs to the *scenario generation*
domain:

- **Agents** — LLM-powered generators for case, skeleton, expansion, map,
  suspects, clues, furniture, critic evaluation, and clearability.
- **Pipeline** — Declarative :class:`PipelineStep` / :class:`PipelineRunner`
  infrastructure with auto-scheduling (topological sort) and disk-based caching.
- **Services** — :class:`ScenarioService` (generation + DB persistence) and
  :class:`SolveService` (deduction scoring).
- **DTOs** — Request/response Pydantic models used by the scenario API
  (``app/models/schemas/scenario/``).
- **State** — :class:`ScenarioStateManager` for crash-recoverable intermediate
  state storage.

Typical import path
-------------------
>>> from app.features.scenario import ScenarioService, SolveService
>>> from app.features.scenario.pipeline import PipelineRunner, PipelineStep
"""
__all__ = [
    "ScenarioService",
    "SolveService",
    "ScenarioStateManager",
    "ScenarioGenerator",
    "ClueGenerator",
    "MapGenerator",
    "SuspectGenerator",
    "ClearabilityEvaluator",
    "ConsistencyValidator",
    "ScenarioRefiner",
    "RefinementResult",
    "RegenLevel",
    "PipelineStep",
    "PipelineRunner",
    "CaseGenerationStep",
    "SkeletonGenerationStep",
    "ExpansionGenerationStep",
    "MapSkeletonStep",
    "SuspectGenerationStep",
    "ClueGenerationStep",
    "FurnitureGenerationStep",
    "MapDetailStep",
]


def __getattr__(name: str):
    if name == "ScenarioService":
        from app.features.scenario.scenario_service import ScenarioService
        return ScenarioService
    if name == "SolveService":
        from app.features.scenario.solve_service import SolveService
        return SolveService
    if name == "ScenarioStateManager":
        from app.features.scenario.scenario_state_manager import ScenarioStateManager
        return ScenarioStateManager
    if name == "ScenarioGenerator":
        from app.features.global_.agent.scenario_generator import ScenarioGenerator
        return ScenarioGenerator
    if name == "ClueGenerator":
        from app.features.global_.agent.clue_generator import ClueGenerator
        return ClueGenerator
    if name == "MapGenerator":
        from app.features.global_.agent.map_generator import MapGenerator
        return MapGenerator
    if name == "SuspectGenerator":
        from app.features.global_.agent.suspect_generator import SuspectGenerator
        return SuspectGenerator
    if name == "ClearabilityEvaluator":
        from app.features.global_.agent.clearability_evaluator import ClearabilityEvaluator
        return ClearabilityEvaluator
    if name == "ConsistencyValidator":
        from app.features.global_.agent.consistency_validator import ConsistencyValidator
        return ConsistencyValidator
    if name == "ScenarioRefiner":
        from app.features.global_.agent.critic import ScenarioRefiner
        return ScenarioRefiner
    if name == "RefinementResult":
        from app.features.global_.agent.critic import RefinementResult
        return RefinementResult
    if name == "RegenLevel":
        from app.features.global_.agent.critic import RegenLevel
        return RegenLevel
    if name in {
        "PipelineStep",
        "PipelineRunner",
        "CaseGenerationStep",
        "SkeletonGenerationStep",
        "ExpansionGenerationStep",
        "MapSkeletonStep",
        "SuspectGenerationStep",
        "ClueGenerationStep",
        "FurnitureGenerationStep",
        "MapDetailStep",
    }:
        from app.features.scenario import pipeline
        return getattr(pipeline, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
