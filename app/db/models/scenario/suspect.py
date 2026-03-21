"""Suspect database models."""
from typing import List, Optional, Any, TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, String, Text, Boolean, Integer, SmallInteger, ForeignKey, ForeignKeyConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.models.scenario.main import Scenario

if TYPE_CHECKING:
    from app.db.models import Location


class Suspect(Base):
    """Suspect."""
    __tablename__ = "suspect"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True, type_=BigInteger)
    suspect_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)

    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)

    is_culprit: Mapped[bool] = mapped_column(Boolean, default=False)
    motive: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alibi_summary: Mapped[str] = mapped_column(Text)

    # Personality
    speech_style: Mapped[str] = mapped_column(String(100))
    emotional_tendency: Mapped[str] = mapped_column(String(100))
    lying_pattern: Mapped[str] = mapped_column(String(50))

    # Image generation prompt
    visual_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Map position (within room)
    location_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    x: Mapped[int] = mapped_column(SmallInteger)
    y: Mapped[int] = mapped_column(SmallInteger)

    # Embedding for RAG (name + role + description)
    profile_embedding = mapped_column(Vector(1024), nullable=True)

    # Relationships
    scenario: Mapped["Scenario"] = relationship(back_populates="suspects")
    location: Mapped["Location"] = relationship(
        primaryjoin="and_(Suspect.scenario_id==Location.scenario_id, Suspect.location_id==Location.location_id)",
        foreign_keys=[scenario_id, location_id],
        overlaps="scenario,suspects"
    )
    facts: Mapped[List["Fact"]] = relationship(
        back_populates="suspect",
        primaryjoin="and_(Suspect.scenario_id==Fact.scenario_id, Suspect.suspect_id==Fact.suspect_id)",
        foreign_keys="[Fact.scenario_id, Fact.suspect_id]",
        viewonly=True
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "location_id"],
            ["location.scenario_id", "location.location_id"],
            ondelete="CASCADE"
        ),
    )


class Fact(Base):
    """Fact - stores both suspect-specific facts (suspect_id > 0) and scenario context (suspect_id = 0)."""
    __tablename__ = "fact"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True, type_=BigInteger)
    fact_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)

    suspect_id: Mapped[int] = mapped_column(BigInteger, default=0)  # 0 = scenario context, >0 = suspect fact
    threshold: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[Any] = mapped_column(JSONB)
    type: Mapped[str] = mapped_column(String(50))
    knowledge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="timeline",
        comment="timeline|heard|secret|hidden for suspect facts; context for suspect_id=0"
    )

    # Embedding for RAG
    embedding = mapped_column(Vector(1024), nullable=True)

    # Optional relationship - only valid when suspect_id > 0
    suspect: Mapped[Optional["Suspect"]] = relationship(
        back_populates="facts",
        primaryjoin="and_(Fact.scenario_id==Suspect.scenario_id, Fact.suspect_id==Suspect.suspect_id)",
        foreign_keys="[Fact.scenario_id, Fact.suspect_id]",
        viewonly=True
    )

    __table_args__ = (
        CheckConstraint("threshold >= 0 AND threshold <= 100", name="check_threshold"),
    )

    def to_string(self, suspect_name: Optional[str] = None) -> str:
        """Return a human-readable representation of this fact.

        The suspect's name can be provided explicitly via `suspect_name` to
        avoid accessing the `suspect` relationship (and thus avoid lazy-loading).
        If no name is provided, the method falls back to using `suspect_id`.
        For context facts (suspect_id=0), returns content directly.
        """
        if self.suspect_id == 0:
            # Context fact - return text content
            if isinstance(self.content, dict) and "text" in self.content:
                return self.content["text"]
            return str(self.content)
        if suspect_name is not None:
            return f"{suspect_name}의 사실 {self.content}"
        return f"용의자 {self.suspect_id}의 사실 {self.content}"
