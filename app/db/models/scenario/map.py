"""Map database model for rooms and corridors."""
from typing import Optional

from sqlalchemy import BigInteger, String, SmallInteger, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Map(Base):
    """Map element (room or corridor) with calculated position."""
    __tablename__ = "map"

    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenario.scenario_id", ondelete="CASCADE"),
        primary_key=True,
        type_=BigInteger
    )
    map_id: Mapped[int] = mapped_column(primary_key=True, type_=BigInteger)

    type: Mapped[str] = mapped_column(String(20))  # 'room' or 'corridor'
    name: Mapped[str] = mapped_column(String(100))

    # Position (bottom-left origin)
    x: Mapped[int] = mapped_column(SmallInteger)
    y: Mapped[int] = mapped_column(SmallInteger)

    # Dimensions
    width: Mapped[int] = mapped_column(SmallInteger)
    height: Mapped[int] = mapped_column(SmallInteger)

    # Additional data (mood for rooms, connections for corridors)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Relationship
    scenario: Mapped["Scenario"] = relationship(back_populates="map_elements")

    __table_args__ = (
        CheckConstraint("type IN ('room', 'corridor')", name="check_map_type"),
    )
