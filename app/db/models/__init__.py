"""Database entity models for MaechuriAIServer.

This package contains **SQLAlchemy ORM** models that map to PostgreSQL
tables.  They are *entities* in the domain-driven sense: they represent
persistent, identity-bearing objects stored in the database.

Object-type boundaries
----------------------
Entities (this package — ``app.db.models``)
    SQLAlchemy ``Base`` subclasses.  Hold persistence logic only.
    Never returned directly by API routes.

DTOs (``app.models.schemas``)
    Pydantic ``BaseModel`` subclasses used for API
    request/response serialisation.

Domain objects (``app.models.domain``)
    Plain Python classes / dataclasses holding runtime business state.

Mapper (``app.db.mappers``)
    :class:`ScenarioMapper` converts between entities and DTOs.
"""
from app.db.models.scenario import (
    Scenario,
    Location,
    Suspect,
    Fact,
    Clue,
    Furniture,
)
from app.db.models.embedding import ChatMessageEmbedding
from app.db.models.game_session import GameSession

__all__ = [
    "Scenario",
    "Location",
    "Suspect",
    "Fact",
    "Clue",
    "Furniture",
    "ChatMessageEmbedding",
    "GameSession",
]
