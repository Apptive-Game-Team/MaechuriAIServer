"""Feature-based package organisation for MaechuriAIServer.

The application is divided into three domains:

``app.features.scenario``
    Everything related to **scenario generation**: LLM agents, declarative
    pipeline, services (:class:`ScenarioService`, :class:`SolveService`),
    and the generation-specific Pydantic DTOs.

``app.features.chat``
    Everything related to **NPC dialogue / interrogation**: suspect-actor
    and pressure-judge agents, :class:`ChatService`, and the chat-specific
    DTOs and domain models.

``app.features.global_``
    **Shared infrastructure** used by both features: LLM client, embedding
    model, RAG pipeline, database sessions, and repositories.

 The ``app.features.*`` packages are the canonical feature-oriented API.
 Legacy service-layer imports under ``app.services.*`` remain as compatibility
 wrappers that forward to the feature packages.
"""
__all__ = ["scenario", "chat", "global_"]
