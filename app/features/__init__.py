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

The existing service-layer packages (``app.services.*``, ``app.models.*``,
``app.db.*``) are still the canonical source; the ``app.features.*`` packages
re-export from them and provide a clean, feature-oriented public API.
"""
from app.features import scenario, chat, global_

__all__ = ["scenario", "chat", "global_"]
