"""Chat message embedding model for conversation history RAG."""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ChatMessageEmbedding(Base):
    """Stores embeddings for chat messages to enable semantic search over conversation history."""
    __tablename__ = "chat_message_embedding"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, type_=BigInteger)

    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenario.scenario_id", ondelete="CASCADE"),
        index=True,
        type_=BigInteger
    )
    session_id: Mapped[str] = mapped_column(String(36), index=True)  # UUID as string

    suspect_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)  # NULL for clue chats
    clue_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)  # NULL for suspect chats

    message_index: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))  # user, suspect, detective
    content: Mapped[str] = mapped_column(Text)

    embedding = mapped_column(Vector(1024))  # BGE-M3 dimension

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
