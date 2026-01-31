"""World-related database models (locations, context)."""
from typing import Optional, List

from sqlalchemy import BigInteger, String, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.database import Base


class Location(Base):
    """Location in scenario with visibility and access rules."""
    __tablename__ = "location"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True, type_=BigInteger)
    location_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)
    name: Mapped[str] = mapped_column(String(100))
    can_see: Mapped[Optional[List]] = mapped_column(JSONB, default=list)  # List of location_ids visible from here
    cannot_see: Mapped[Optional[List]] = mapped_column(JSONB, default=list)  # List of location_ids not visible from here
    access_requires: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Access requirement

    scenario: Mapped["Scenario"] = relationship(back_populates="locations")


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
