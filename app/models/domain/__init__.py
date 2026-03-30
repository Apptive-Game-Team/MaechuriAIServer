"""Domain objects — runtime business state for MaechuriAIServer.

Domain objects represent in-memory state that drives game logic.  They are
distinct from:

- **DTOs** (``app.models.schemas``): Pydantic models used for API
  serialisation and service communication.
- **Entities** (``app.db.models``): SQLAlchemy ORM models that map to
  database rows.

Domain objects in this package
--------------------------------
:class:`Suspect`
    Full in-memory suspect loaded for interrogation.  Built from a
    persisted :class:`SuspectSchema` DTO plus live game-session context.
:class:`SuspectState`
    Per-session runtime pressure / clue-seen tracking.  Loaded from and
    persisted back to :class:`GameSession` (entity).
:class:`AnsweringRule` / :class:`TruthModel`
    NPC behaviour rules that govern how a suspect answers questions.
:class:`TimeMemory` / :class:`Observation`
    NPC memory structures used by the actor LLM.
:class:`DialogueState`
    Tracks conversation flow state for a single interrogation session.
"""
from .answering_rule import AnsweringRule
from .dialogue_state import DialogueState
from .observation import Observation
from .suspect import Suspect
from .time_memory import TimeMemory
from .truth_model import TruthModel

__all__ = [
    "AnsweringRule",
    "DialogueState",
    "Observation",
    "Suspect",
    "TimeMemory",
    "TruthModel",
]
