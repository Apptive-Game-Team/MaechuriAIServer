"""RAG Indexer for generating and storing embeddings."""

from typing import List, Optional
import logging

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Suspect,
    SuspectTimeline,
    SuspectSecret,
    Clue,
    ChatMessageEmbedding,
)
from app.services.embedding import get_embedding_service, EmbeddingService


logger = logging.getLogger(__name__)  # log 추적용


class RAGIndexer:
    """Generates and stores embeddings for scenario data.

    This service is responsible for:
    - Generating embeddings when scenarios are created
    - Updating embeddings when data changes
    - Storing chat message embeddings during conversations
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """Initialize the RAG indexer.

        Parameters
        ----------
        embedding_service : EmbeddingService, optional
            The embedding service to use. Uses singleton if not provided.
        """
        self.embedding_service = embedding_service or get_embedding_service()

    async def index_scenario(self, db: AsyncSession, scenario_id: int) -> dict:
        """Index all data for a scenario.

        Generates and stores embeddings for all suspects, timelines, secrets, and clues
        in the given scenario.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID to index.

        Returns
        -------
        dict
            Statistics about indexed items.
        """
        # Index suspects, timelines, and secrets
        suspect_stats = await self.index_suspects(db, scenario_id)
        
        # Index clues
        clues_indexed = await self.index_clues(db, scenario_id)
        
        stats = {
            "suspects": suspect_stats["suspects"],
            "timelines": suspect_stats["timelines"],
            "secrets": suspect_stats["secrets"],
            "clues": clues_indexed,
        }

        await db.commit()

        logger.info(f"Indexed scenario {scenario_id}: {stats}")
        return stats

    async def index_suspects(self, db: AsyncSession, scenario_id: int) -> dict:
        """Index all suspects in a scenario.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.

        Returns
        -------
        dict
            Stats containing number of suspects, timelines, and secrets indexed.
        """
        from sqlalchemy import select, bindparam
        from sqlalchemy.orm import selectinload

        # Load suspects with relationships
        result = await db.execute(
            select(Suspect)
            .where(Suspect.scenario_id == scenario_id)
            .options(selectinload(Suspect.timeline), selectinload(Suspect.secrets))
        )
        suspects = result.scalars().all()

        suspect_updates = []
        timeline_updates = []
        secret_updates = []
        
        for suspect in suspects:
            # Index suspect profile
            profile_embedding = self.embedding_service.embed_suspect_profile(
                name=suspect.name,
                role=suspect.role,
                description=suspect.description,
                age=suspect.age,
                gender=suspect.gender,
            )
            suspect_updates.append({
                "scenario_id": scenario_id,
                "suspect_id": suspect.suspect_id,
                "profile_embedding": profile_embedding
            })

            # Index timelines
            for timeline in suspect.timeline:
                timeline_embedding = self.embedding_service.embed_timeline_entry(
                    time_range=timeline.time_range,
                    location=timeline.location,
                    activity=timeline.activity,
                    suspect_name=suspect.name,
                )
                timeline_updates.append({
                    "scenario_id": scenario_id,
                    "suspect_id": suspect.suspect_id,
                    "timeline_id": timeline.timeline_id,
                    "embedding": timeline_embedding
                })

            # Index secrets
            for secret in suspect.secrets:
                secret_embedding = self.embedding_service.embed_secret(
                    content=secret.content, suspect_name=suspect.name
                )
                secret_updates.append({
                    "scenario_id": scenario_id,
                    "suspect_id": suspect.suspect_id,
                    "secret_id": secret.secret_id,
                    "embedding": secret_embedding
                })

        # Bulk updates
        if suspect_updates:
            await db.execute(
                update(Suspect)
                .where(
                    Suspect.scenario_id == bindparam("scenario_id"),
                    Suspect.suspect_id == bindparam("suspect_id")
                )
                .values(profile_embedding=bindparam("profile_embedding")),
                suspect_updates
            )

        if timeline_updates:
            await db.execute(
                update(SuspectTimeline)
                .where(
                    SuspectTimeline.scenario_id == bindparam("scenario_id"),
                    SuspectTimeline.suspect_id == bindparam("suspect_id"),
                    SuspectTimeline.timeline_id == bindparam("timeline_id")
                )
                .values(embedding=bindparam("embedding")),
                timeline_updates
            )

        if secret_updates:
            await db.execute(
                update(SuspectSecret)
                .where(
                    SuspectSecret.scenario_id == bindparam("scenario_id"),
                    SuspectSecret.suspect_id == bindparam("suspect_id"),
                    SuspectSecret.secret_id == bindparam("secret_id")
                )
                .values(embedding=bindparam("embedding")),
                secret_updates
            )

        return {
            "suspects": len(suspect_updates),
            "timelines": len(timeline_updates),
            "secrets": len(secret_updates)
        }

    async def index_clues(self, db: AsyncSession, scenario_id: int) -> int:
        """Index all clues in a scenario.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.

        Returns
        -------
        int
            Number of clues indexed.
        """
        from sqlalchemy import select, bindparam

        result = await db.execute(select(Clue).where(Clue.scenario_id == scenario_id))
        clues = result.scalars().all()

        clue_updates = []
        for clue in clues:
            # Index description
            description_embedding = self.embedding_service.embed_clue_description(
                name=clue.name, description=clue.description, found_at=clue.found_at
            )

            # Index logic explanation
            logic_embedding = self.embedding_service.embed_clue_logic(
                name=clue.name,
                logic_explanation=clue.logic_explanation,
                decoded_answer=clue.decoded_answer,
            )

            clue_updates.append({
                "scenario_id": scenario_id,
                "clue_id": clue.clue_id,
                "description_embedding": description_embedding,
                "logic_embedding": logic_embedding
            })

        if clue_updates:
            await db.execute(
                update(Clue)
                .where(
                    Clue.scenario_id == bindparam("scenario_id"),
                    Clue.clue_id == bindparam("clue_id")
                )
                .values(
                    description_embedding=bindparam("description_embedding"),
                    logic_embedding=bindparam("logic_embedding"),
                ),
                clue_updates
            )

        return len(clue_updates)

    async def index_chat_message(
        self,
        db: AsyncSession,
        scenario_id: int,
        session_id: str,
        message_index: int,
        role: str,
        content: str,
        suspect_id: Optional[int] = None,
        clue_id: Optional[int] = None,
        context: str = "",
    ) -> int:
        """Index a single chat message.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        session_id : str
            Unique session identifier (UUID).
        message_index : int
            Index of message in conversation.
        role : str
            Message role (user, suspect, detective).
        content : str
            Message content.
        suspect_id : int, optional
            Suspect ID if this is a suspect chat.
        clue_id : int, optional
            Clue ID if this is a clue chat.
        context : str, optional
            Additional context for embedding.

        Returns
        -------
        int
            The created message embedding ID.
        """
        embedding = self.embedding_service.embed_chat_message(
            role=role, content=content, context=context
        )

        message_embedding = ChatMessageEmbedding(
            scenario_id=scenario_id,
            session_id=session_id,
            suspect_id=suspect_id,
            clue_id=clue_id,
            message_index=message_index,
            role=role,
            content=content,
            embedding=embedding,
        )

        db.add(message_embedding)
        await db.flush()

        return message_embedding.id

    async def index_chat_messages_batch(
        self,
        db: AsyncSession,
        scenario_id: int,
        session_id: str,
        messages: List[dict],
        suspect_id: Optional[int] = None,
        clue_id: Optional[int] = None,
        context: str = "",
    ) -> List[int]:
        """Index multiple chat messages in batch.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        session_id : str
            Unique session identifier.
        messages : List[dict]
            List of messages with 'role' and 'content' keys.
        suspect_id : int, optional
            Suspect ID if this is a suspect chat.
        clue_id : int, optional
            Clue ID if this is a clue chat.
        context : str, optional
            Additional context for embedding.

        Returns
        -------
        List[int]
            List of created message embedding IDs.
        """
        if not messages:
            return []

        # Prepare texts for batch embedding
        texts = []
        role_map = {"user": "탐정", "detective": "탐정", "suspect": "용의자"}

        for msg in messages:
            role_label = role_map.get(msg["role"], msg["role"])
            if context:
                text = f"[{context}] {role_label}: {msg['content']}"
            else:
                text = f"{role_label}: {msg['content']}"
            texts.append(text)

        # Generate embeddings in batch
        embeddings = self.embedding_service.embed_batch_texts(texts)

        # Create message embedding records
        ids = []
        for i, (msg, embedding) in enumerate(zip(messages, embeddings)):
            message_embedding = ChatMessageEmbedding(
                scenario_id=scenario_id,
                session_id=session_id,
                suspect_id=suspect_id,
                clue_id=clue_id,
                message_index=i,
                role=msg["role"],
                content=msg["content"],
                embedding=embedding,
            )
            db.add(message_embedding)

        await db.flush()

        # Get IDs (need to refresh to get auto-generated IDs)
        # For simplicity, we return empty list here - caller can query if needed
        return ids


# Singleton instance
_indexer_instance: Optional[RAGIndexer] = None


def get_rag_indexer() -> RAGIndexer:
    """Get the singleton RAG indexer instance.

    Returns
    -------
    RAGIndexer
        The RAG indexer instance.
    """
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = RAGIndexer()
    return _indexer_instance
