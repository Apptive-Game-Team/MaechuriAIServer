"""Chat / NPC-dialogue feature package.

This package groups every component that belongs to the *chat and NPC
dialogue* domain:

- **Agents** — LLM-powered agents for suspect roleplay
  (:class:`SuspectActor`), pressure evaluation (:class:`PressureJudge`),
  clue analysis (:class:`ClueAgent`), and detective assistance
  (:class:`DetectiveAgent`).
- **Services** — :class:`ChatService` orchestrates full interrogation /
  clue-analysis / detective-chat flows with RAG context retrieval.
- **DTOs** — Request/response Pydantic models for chat API endpoints
  (``app/models/schemas/chat/``, ``app/models/schemas/pressure.py``).
- **Domain** — :class:`SuspectState` (runtime pressure / clue-seen state
  per session), :class:`Suspect` (domain model used during interrogation).

Typical import path
-------------------
>>> from app.features.chat import ChatService
>>> from app.features.chat import PressureJudge, SuspectActor
"""
__all__ = [
    "ChatService",
    "PressureJudge",
    "SuspectActor",
    "ClueAgent",
    "DetectiveAgent",
    "Suspect",
    "SuspectState",
]


def __getattr__(name: str):
    if name == "ChatService":
        from app.features.chat.chat_service import ChatService
        return ChatService
    if name == "PressureJudge":
        from app.features.global_.agent.pressure_judge import PressureJudge
        return PressureJudge
    if name == "SuspectActor":
        from app.features.global_.agent.suspect_actor import SuspectActor
        return SuspectActor
    if name == "ClueAgent":
        from app.features.global_.agent.clue_agent import ClueAgent
        return ClueAgent
    if name == "DetectiveAgent":
        from app.features.global_.agent.detective_agent import DetectiveAgent
        return DetectiveAgent
    if name == "Suspect":
        from app.models.domain.suspect import Suspect
        return Suspect
    if name == "SuspectState":
        from app.models.domain.suspect_state import SuspectState
        return SuspectState
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
