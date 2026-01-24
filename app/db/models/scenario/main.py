"""Main scenario database model."""
from datetime import time, datetime
from typing import List

from sqlalchemy import String, Text, Boolean, Time, CheckConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Scenario(Base):
    """Root scenario table."""
    __tablename__ = "scenario"

    scenario_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Meta
    difficulty: Mapped[str] = mapped_column(String(10))
    theme: Mapped[str] = mapped_column(String(100))
    tone: Mapped[str] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), default="ko")

    # Incident
    incident_type: Mapped[str] = mapped_column(String(100))
    incident_summary: Mapped[str] = mapped_column(Text)
    incident_time_start: Mapped[time] = mapped_column(Time)
    incident_time_end: Mapped[time] = mapped_column(Time)
    incident_location: Mapped[str] = mapped_column(String(100))
    primary_object: Mapped[str] = mapped_column(String(100))

    # Ground Truth
    crime_time_start: Mapped[time] = mapped_column(Time)
    crime_time_end: Mapped[time] = mapped_column(Time)
    crime_location: Mapped[str] = mapped_column(String(100))
    crime_method: Mapped[str] = mapped_column(Text)

    # Constraints
    no_supernatural: Mapped[bool] = mapped_column(Boolean, default=True)
    no_time_travel: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    locations: Mapped[List["Location"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    visibility_rules: Mapped[List["VisibilityRule"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    access_rules: Mapped[List["AccessRule"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    required_clues: Mapped[List["RequiredClue"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    suspects: Mapped[List["Suspect"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    clues: Mapped[List["Clue"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    game_sessions: Mapped[List["GameSession"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'mid', 'hard')", name="check_difficulty"),
    )
