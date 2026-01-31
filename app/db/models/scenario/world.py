"""World-related database models (locations)."""
from typing import Optional, List

from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
