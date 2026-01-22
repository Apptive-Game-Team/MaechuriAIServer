"""Suspect database models."""
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, ForeignKeyConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Suspect(Base):
    """Suspect."""
    __tablename__ = "suspect"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    suspect_id: Mapped[int] = mapped_column(primary_key=True)

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

    critical_evidence_ids: Mapped[list] = mapped_column(JSONB, default=list)

    # Embedding for RAG (name + role + description)
    profile_embedding = mapped_column(Vector(1024), nullable=True)

    # Relationships
    scenario: Mapped["Scenario"] = relationship(back_populates="suspects")
    timeline: Mapped[List["SuspectTimeline"]] = relationship(back_populates="suspect", cascade="all, delete-orphan")
    secrets: Mapped[List["SuspectSecret"]] = relationship(back_populates="suspect", cascade="all, delete-orphan")


class SuspectTimeline(Base):
    """Suspect timeline."""
    __tablename__ = "suspect_timeline"

    scenario_id: Mapped[int] = mapped_column(primary_key=True)
    suspect_id: Mapped[int] = mapped_column(primary_key=True)
    timeline_id: Mapped[int] = mapped_column(primary_key=True)

    time_range: Mapped[str] = mapped_column(String(50))
    location: Mapped[str] = mapped_column(String(100))
    activity: Mapped[str] = mapped_column(Text)
    can_prove: Mapped[bool] = mapped_column(Boolean, default=False)
    witness: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Embedding for RAG (time_range + location + activity)
    embedding = mapped_column(Vector(1024), nullable=True)

    suspect: Mapped["Suspect"] = relationship(back_populates="timeline")

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "suspect_id"],
            ["suspect.scenario_id", "suspect.suspect_id"],
            ondelete="CASCADE"
        ),
    )


class SuspectSecret(Base):
    """Suspect secret."""
    __tablename__ = "suspect_secret"

    scenario_id: Mapped[int] = mapped_column(primary_key=True)
    suspect_id: Mapped[int] = mapped_column(primary_key=True)
    secret_id: Mapped[int] = mapped_column(primary_key=True)

    threshold: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    trigger_evidence_ids: Mapped[list] = mapped_column(JSONB, default=list)

    # Embedding for RAG (secret content)
    embedding = mapped_column(Vector(1024), nullable=True)

    suspect: Mapped["Suspect"] = relationship(back_populates="secrets")

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "suspect_id"],
            ["suspect.scenario_id", "suspect.suspect_id"],
            ondelete="CASCADE"
        ),
        CheckConstraint("threshold >= 0 AND threshold <= 100", name="check_threshold"),
    )
