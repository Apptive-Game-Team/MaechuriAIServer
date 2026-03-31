"""Furniture database model."""
from typing import Optional

from sqlalchemy import BigInteger, Integer, String, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Furniture(Base):
    """Furniture placed inside a room on the map."""
    __tablename__ = "furniture"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    location_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Position & size on map grid (room-relative)
    origin_x: Mapped[int] = mapped_column(Integer)
    origin_y: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)

    assets_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("asset.id"), nullable=True
    )

    asset: Mapped[Optional["Asset"]] = relationship(foreign_keys=[assets_id], viewonly=True)

    location: Mapped["Location"] = relationship(
        foreign_keys=[scenario_id, location_id],
        viewonly=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["scenario_id", "location_id"],
            ["location.scenario_id", "location.location_id"],
            ondelete="CASCADE",
        ),
    )
