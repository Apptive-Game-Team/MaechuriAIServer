"""
SQLAlchemy ORM models matching schema.sql
"""
from datetime import time, datetime
from typing import List, Optional

from sqlalchemy import String, Text, Boolean, Integer, Time, ForeignKey, ForeignKeyConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Scenario(Base):
    """시나리오 루트 테이블"""
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

    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # Relationships
    locations: Mapped[List["Location"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    visibility_rules: Mapped[List["VisibilityRule"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    access_rules: Mapped[List["AccessRule"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    required_evidences: Mapped[List["RequiredEvidence"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    suspects: Mapped[List["Suspect"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    clues: Mapped[List["Clue"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'mid', 'hard')", name="check_difficulty"),
    )


class Location(Base):
    """시나리오 내 장소"""
    __tablename__ = "location"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    location_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    scenario: Mapped["Scenario"] = relationship(back_populates="locations")


class VisibilityRule(Base):
    """가시성 규칙"""
    __tablename__ = "visibility_rule"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    rule_id: Mapped[int] = mapped_column(primary_key=True)
    from_location: Mapped[str] = mapped_column(String(100))
    can_see: Mapped[list] = mapped_column(JSONB, default=list)
    cannot_see: Mapped[list] = mapped_column(JSONB, default=list)
    evidence_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    scenario: Mapped["Scenario"] = relationship(back_populates="visibility_rules")


class AccessRule(Base):
    """접근 규칙"""
    __tablename__ = "access_rule"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    rule_id: Mapped[int] = mapped_column(primary_key=True)
    location: Mapped[str] = mapped_column(String(100))
    requires: Mapped[str] = mapped_column(String(100))

    scenario: Mapped["Scenario"] = relationship(back_populates="access_rules")


class RequiredEvidence(Base):
    """필수 증거"""
    __tablename__ = "required_evidence"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    evidence_id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    min_count: Mapped[int] = mapped_column(Integer)

    scenario: Mapped["Scenario"] = relationship(back_populates="required_evidences")

    __table_args__ = (
        CheckConstraint("min_count >= 1", name="check_min_count"),
    )


class Suspect(Base):
    """용의자"""
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

    # Relationships
    scenario: Mapped["Scenario"] = relationship(back_populates="suspects")
    timeline: Mapped[List["SuspectTimeline"]] = relationship(back_populates="suspect", cascade="all, delete-orphan")
    secrets: Mapped[List["SuspectSecret"]] = relationship(back_populates="suspect", cascade="all, delete-orphan")


class SuspectTimeline(Base):
    """용의자 타임라인"""
    __tablename__ = "suspect_timeline"

    scenario_id: Mapped[int] = mapped_column(primary_key=True)
    suspect_id: Mapped[int] = mapped_column(primary_key=True)
    timeline_id: Mapped[int] = mapped_column(primary_key=True)

    time_range: Mapped[str] = mapped_column(String(50))
    location: Mapped[str] = mapped_column(String(100))
    activity: Mapped[str] = mapped_column(Text)
    can_prove: Mapped[bool] = mapped_column(Boolean, default=False)
    witness: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    suspect: Mapped["Suspect"] = relationship(back_populates="timeline")

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "suspect_id"],
            ["suspect.scenario_id", "suspect.suspect_id"],
            ondelete="CASCADE"
        ),
    )


class SuspectSecret(Base):
    """용의자 비밀"""
    __tablename__ = "suspect_secret"

    scenario_id: Mapped[int] = mapped_column(primary_key=True)
    suspect_id: Mapped[int] = mapped_column(primary_key=True)
    secret_id: Mapped[int] = mapped_column(primary_key=True)

    threshold: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    trigger_evidence_ids: Mapped[list] = mapped_column(JSONB, default=list)

    suspect: Mapped["Suspect"] = relationship(back_populates="secrets")

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "suspect_id"],
            ["suspect.scenario_id", "suspect.suspect_id"],
            ondelete="CASCADE"
        ),
        CheckConstraint("threshold >= 0 AND threshold <= 100", name="check_threshold"),
    )


class Clue(Base):
    """단서"""
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
