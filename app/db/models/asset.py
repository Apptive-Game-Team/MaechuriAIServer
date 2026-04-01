"""Asset database model."""
import enum
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AssetType(str, enum.Enum):
    """The game entity type this asset represents."""
    FURNITURE = "furniture"
    SUSPECT = "suspect"
    CLUE = "clue"


class Asset(Base):
    """Asset table for storing generated image/resource metadata and prompt embeddings."""
    __tablename__ = "asset"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)

    type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Entity type: furniture, suspect, clue"
    )

    final_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    resized_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="COMPLETED", server_default="COMPLETED")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # BGE-M3 embedding of the prompt field (1024 dimensions)
    embedding = mapped_column(Vector(1024), nullable=True)
