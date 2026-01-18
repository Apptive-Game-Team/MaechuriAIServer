"""Clue database model."""
from typing import Optional

from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Clue(Base):
    """Clue."""
    __tablename__ = "clue"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    clue_id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(100))
    found_at: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    related_suspect_ids: Mapped[list] = mapped_column(JSONB, default=list)
    logic_explanation: Mapped[str] = mapped_column(Text)
    decoded_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_red_herring: Mapped[bool] = mapped_column(Boolean, default=False)

    scenario: Mapped["Scenario"] = relationship(back_populates="clues")
