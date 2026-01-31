"""Main scenario database model."""
from datetime import time, datetime
from typing import List, Optional

from sqlalchemy import BigInteger, String, Text, Boolean, Time, CheckConstraint, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.database import Base


class Scenario(Base):
    """Root scenario table."""
    __tablename__ = "scenario"

    scenario_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, type_=BigInteger)

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
    incident_location_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    primary_object: Mapped[str] = mapped_column(String(100))

    # Ground Truth
    crime_time_start: Mapped[time] = mapped_column(Time)
    crime_time_end: Mapped[time] = mapped_column(Time)
    crime_location_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    crime_method: Mapped[str] = mapped_column(Text)

    # Constraints
    no_supernatural: Mapped[bool] = mapped_column(Boolean, default=True)
    no_time_travel: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    locations: Mapped[List["Location"]] = relationship(back_populates="scenario", cascade="all, delete-orphan", foreign_keys="Location.scenario_id")
    
    incident_loc: Mapped["Location"] = relationship(
        "Location",
        primaryjoin="and_(Scenario.scenario_id==Location.scenario_id, Scenario.incident_location_id==Location.location_id)",
        foreign_keys="[Location.scenario_id, Location.location_id]",
        viewonly=True,
        post_update=True
    )
    
    crime_loc: Mapped["Location"] = relationship(
        "Location",
        primaryjoin="and_(Scenario.scenario_id==Location.scenario_id, Scenario.crime_location_id==Location.location_id)",
        foreign_keys="[Location.scenario_id, Location.location_id]",
        viewonly=True,
        post_update=True
    )

    suspects: Mapped[List["Suspect"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    clues: Mapped[List["Clue"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    contexts: Mapped[List["ScenarioContext"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    game_sessions: Mapped[List["GameSession"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    map_elements: Mapped[List["Map"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'mid', 'hard')", name="check_difficulty"),
        # Foreign keys for location refs are handled via ALTER TABLE or explicit ForeignKeyConstraint if needed,
        # but since it's a circular ref (Scenario needs Location, Location needs Scenario), we handle it carefully.
        # Here we just define columns.
    )


class ScenarioContext(Base):
    """
    조력자(형사)가 참조하는 공개 가능한 컨텍스트 정보.
    RAG를 통해 시나리오 전반적인 질문에 답변할 때 사용.
    ground_truth, suspect 민감 정보는 절대 저장하지 않음.
    """
    __tablename__ = "scenario_context"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True, type_=BigInteger)
    context_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)
    type: Mapped[str] = mapped_column(String(50))  # 'incident', 'location', 'world'
    content: Mapped[str] = mapped_column(Text)  # RAG용 자연어 텍스트
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)  # 원본 데이터
    embedding = mapped_column(Vector(1024), nullable=True)

    scenario: Mapped["Scenario"] = relationship(back_populates="contexts")

    __table_args__ = (
        CheckConstraint("type IN ('incident', 'location', 'world')", name="check_context_type"),
    )
