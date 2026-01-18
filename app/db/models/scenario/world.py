"""World-related database models (locations, rules)."""
from typing import Optional

from sqlalchemy import String, ForeignKey, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Location(Base):
    """Location in scenario."""
    __tablename__ = "location"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    location_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    scenario: Mapped["Scenario"] = relationship(back_populates="locations")


class VisibilityRule(Base):
    """Visibility rules."""
    __tablename__ = "visibility_rule"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    rule_id: Mapped[int] = mapped_column(primary_key=True)
    from_location: Mapped[str] = mapped_column(String(100))
    can_see: Mapped[list] = mapped_column(JSONB, default=list)
    cannot_see: Mapped[list] = mapped_column(JSONB, default=list)
    evidence_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    scenario: Mapped["Scenario"] = relationship(back_populates="visibility_rules")


class AccessRule(Base):
    """Access rules."""
    __tablename__ = "access_rule"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    rule_id: Mapped[int] = mapped_column(primary_key=True)
    location: Mapped[str] = mapped_column(String(100))
    requires: Mapped[str] = mapped_column(String(100))

    scenario: Mapped["Scenario"] = relationship(back_populates="access_rules")


class RequiredEvidence(Base):
    """Required evidence."""
    __tablename__ = "required_evidence"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    evidence_id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    min_count: Mapped[int] = mapped_column(Integer)

    scenario: Mapped["Scenario"] = relationship(back_populates="required_evidences")

    __table_args__ = (
        CheckConstraint("min_count >= 1", name="check_min_count"),
    )
