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
# Service
from app.services.npc.chat_service import ChatService

# Agents
from app.services.agent.pressure_judge import PressureJudge
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.clue_agent import ClueAgent
from app.services.agent.detective_agent import DetectiveAgent

# Domain models
from app.models.domain.suspect import Suspect
from app.models.domain.suspect_state import SuspectState

__all__ = [
    # Service
    "ChatService",
    # Agents
    "PressureJudge",
    "SuspectActor",
    "ClueAgent",
    "DetectiveAgent",
    # Domain
    "Suspect",
    "SuspectState",
]
