"""World-related database models (locations)."""
from typing import Optional, List

from sqlalchemy import BigInteger, String, SmallInteger, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Location(Base):
    """Location in scenario with visibility, access rules, and map geometry."""
    __tablename__ = "location"

    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.scenario_id", ondelete="CASCADE"), primary_key=True, type_=BigInteger)
    location_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20), default="room")

    # Map geometry (null when no map data)
    x: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    y: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Visibility and access (rooms only)
    can_see: Mapped[Optional[List]] = mapped_column(JSONB, default=list)
    cannot_see: Mapped[Optional[List]] = mapped_column(JSONB, default=list)
    access_requires: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    scenario: Mapped["Scenario"] = relationship(back_populates="locations")

    __table_args__ = (
        CheckConstraint("type IN ('room', 'corridor')", name="check_location_type"),
    )
