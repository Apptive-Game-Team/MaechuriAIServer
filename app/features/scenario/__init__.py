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
# Services
from app.services.scenario.scenario_service import ScenarioService
from app.services.scenario.solve_service import SolveService
from app.services.scenario.scenario_state_manager import ScenarioStateManager

# Agents
from app.services.agent.scenario_generator import ScenarioGenerator
from app.services.agent.clue_generator import ClueGenerator
from app.services.agent.map_generator import MapGenerator
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.agent.clearability_evaluator import ClearabilityEvaluator
from app.services.agent.consistency_validator import ConsistencyValidator
from app.services.agent.critic import ScenarioRefiner, RefinementResult, RegenLevel

# Declarative pipeline
from app.services.scenario.pipeline import (
    PipelineStep,
    PipelineRunner,
    CaseGenerationStep,
    SkeletonGenerationStep,
    ExpansionGenerationStep,
    MapSkeletonStep,
    SuspectGenerationStep,
    ClueGenerationStep,
    FurnitureGenerationStep,
    MapDetailStep,
)

__all__ = [
    # Services
    "ScenarioService",
    "SolveService",
    "ScenarioStateManager",
    # Agents
    "ScenarioGenerator",
    "ClueGenerator",
    "MapGenerator",
    "SuspectGenerator",
    "ClearabilityEvaluator",
    "ConsistencyValidator",
    "ScenarioRefiner",
    "RefinementResult",
    "RegenLevel",
    # Pipeline
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
