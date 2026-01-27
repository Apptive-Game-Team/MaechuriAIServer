"""Suspect database models."""
from typing import List, Optional, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, String, Text, Boolean, Integer, ForeignKey, ForeignKeyConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.models.scenario.main import Scenario


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

    critical_clue_ids: Mapped[list] = mapped_column(JSONB, default=list)

    # Embedding for RAG (name + role + description)
    profile_embedding = mapped_column(Vector(1024), nullable=True)

    # Relationships
    scenario: Mapped["Scenario"] = relationship(back_populates="suspects")
    facts: Mapped[List["Fact"]] = relationship(back_populates="suspect", cascade="all, delete-orphan")

class Fact(Base):
    """Suspect fact."""
    __tablename__ = "fact"

    scenario_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)
    fact_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)

    threshold: Mapped[int] = mapped_column(Integer)
    content: Mapped[Any] = mapped_column(JSONB)

    type: Mapped[str] = mapped_column(String(50))

    # Embedding for RAG (secret content)
    embedding = mapped_column(Vector(1024), nullable=True)

    suspect_id: Mapped[int] = mapped_column(BigInteger)

    suspect: Mapped[Suspect] = relationship(back_populates="facts")

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "suspect_id"],
            ["suspect.scenario_id", "suspect.suspect_id"],
            ondelete="CASCADE"
        ),
        CheckConstraint("threshold >= 0 AND threshold <= 100", name="check_threshold"),
    )

    def to_string(self) -> str:
        return f"{self.suspect.name}의 사실 {self.content}"

