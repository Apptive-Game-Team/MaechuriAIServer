"""Clue database model."""
from typing import Optional, TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, String, Text, Boolean, ForeignKey, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.db.models import Location, Scenario


class Clue(Base):
    """Clue."""
    __tablename__ = "clue"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True, type_=BigInteger)
    clue_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)

    name: Mapped[str] = mapped_column(String(100))
    location_id: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(Text)
    related_fact_ids: Mapped[list] = mapped_column(JSONB, default=list)
    logic_explanation: Mapped[str] = mapped_column(Text)
    decoded_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_red_herring: Mapped[bool] = mapped_column(Boolean, default=False)

    # Embeddings for RAG
    description_embedding = mapped_column(Vector(1024), nullable=True)
    logic_embedding = mapped_column(Vector(1024), nullable=True)

    scenario: Mapped["Scenario"] = relationship(back_populates="clues")
    location: Mapped["Location"] = relationship(
        primaryjoin="and_(Clue.scenario_id==Location.scenario_id, Clue.location_id==Location.location_id)",
        foreign_keys=[scenario_id, location_id],
        overlaps="scenario,clues"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "location_id"],
            ["location.scenario_id", "location.location_id"],
            ondelete="CASCADE"
        ),
    )
