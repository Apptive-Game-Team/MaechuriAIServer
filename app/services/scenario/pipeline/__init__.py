"""Declarative scenario generation pipeline.

The pipeline is split into two phases that mirror the two retry loops in
:class:`ScenarioService`:

Narrative pipeline
    :class:`CaseGenerationStep` → :class:`SkeletonGenerationStep` →
    :class:`ExpansionGenerationStep`

    Steps are potentially re-run when the critic loop requests skeleton or
    expansion regeneration.

Content pipeline
    :class:`MapSkeletonStep` → :class:`SuspectGenerationStep` /
    :class:`ClueGenerationStep` / :class:`FurnitureGenerationStep` →
    :class:`MapDetailStep`

    Suspects and clues are re-run when the clearability check fails.
"""
from .step import PipelineStep
from .runner import PipelineRunner
from .steps import (
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
