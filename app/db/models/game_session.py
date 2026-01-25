"""Game session model for managing player game state."""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class GameSession(Base):
    """Game session tracking player progress and state.

    Uses composite primary key (session_id, scenario_id) to allow
    one user to play multiple scenarios simultaneously.
    """
    __tablename__ = "game_session"

    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenario.scenario_id", ondelete="CASCADE"),
        primary_key=True,
        type_=BigInteger
    )

    # Game state - suspect interrogation
    current_pressure: Mapped[int] = mapped_column(Integer, default=0)
    suspect_pressures: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Per-suspect pressure: {suspect_id: pressure_value}"
    )
    clue_seen_ids: Mapped[list] = mapped_column(JSONB, default=list)

    # Progress tracking
    suspect_interactions: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Track interactions per suspect: {suspect_id: interaction_count}"
    )
    clue_interactions: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Track clue analysis: {clue_id: analyzed_count}"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    scenario: Mapped["Scenario"] = relationship(back_populates="game_sessions")
