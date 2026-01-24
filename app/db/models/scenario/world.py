"""World-related database models (locations, rules)."""
from typing import Optional

from sqlalchemy import String, ForeignKey, Integer, CheckConstraint, ForeignKeyConstraint
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
    from_location_id: Mapped[int] = mapped_column(Integer)
    can_see: Mapped[list] = mapped_column(JSONB, default=list) # List of location_ids
    cannot_see: Mapped[list] = mapped_column(JSONB, default=list) # List of location_ids
    clue_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    scenario: Mapped["Scenario"] = relationship(back_populates="visibility_rules")
    from_location: Mapped["Location"] = relationship(
        primaryjoin="and_(VisibilityRule.scenario_id==Location.scenario_id, VisibilityRule.from_location_id==Location.location_id)",
        foreign_keys=[scenario_id, from_location_id]
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "from_location_id"],
            ["location.scenario_id", "location.location_id"],
            ondelete="CASCADE"
        ),
    )


class AccessRule(Base):
    """Access rules."""
    __tablename__ = "access_rule"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    rule_id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer)
    requires: Mapped[str] = mapped_column(String(100))

    scenario: Mapped["Scenario"] = relationship(back_populates="access_rules")
    target_location: Mapped["Location"] = relationship(
        primaryjoin="and_(AccessRule.scenario_id==Location.scenario_id, AccessRule.location_id==Location.location_id)",
        foreign_keys=[scenario_id, location_id]
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "location_id"],
            ["location.scenario_id", "location.location_id"],
            ondelete="CASCADE"
        ),
    )


class RequiredClue(Base):
    """Required clue."""
    __tablename__ = "required_clue"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True)
    clue_id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    min_count: Mapped[int] = mapped_column(Integer)

    scenario: Mapped["Scenario"] = relationship(back_populates="required_clues")

    __table_args__ = (
        CheckConstraint("min_count >= 1", name="check_min_count"),
    )
