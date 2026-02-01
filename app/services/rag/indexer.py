"""RAG Indexer for generating and storing embeddings."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Suspect,
    Fact,
    Clue,
    ChatMessageEmbedding,
    Location
)
from app.services.embedding import get_embedding_service, EmbeddingService


logger = logging.getLogger(__name__)

class BaseIndexer(ABC):
    """Abstract base class for entity indexers."""

    @abstractmethod
    async def index(
        self,
        db: AsyncSession,
        scenario_id: int,
        embedding_service: EmbeddingService
    ) -> Dict[str, int]:
        """Index entities for a scenario.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID to index.
        embedding_service : EmbeddingService
            The embedding service to use.

        Returns
        -------
        Dict[str, int]
            Statistics about indexed items.
        """
        pass


class SuspectIndexer(BaseIndexer):
    """Indexer for suspects and their facts."""

    async def index(
        self,
        db: AsyncSession,
        scenario_id: int,
        embedding_service: EmbeddingService
    ) -> Dict[str, int]:
        """Index all suspects and facts in a scenario."""
        result = await db.execute(
            select(Suspect)
            .where(Suspect.scenario_id == scenario_id)
            .options(selectinload(Suspect.facts))
        )
        suspects = result.scalars().all()

        suspect_updates = []
        fact_updates = []

        for suspect in suspects:
            profile_embedding = embedding_service.embed_suspect_profile(
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

            for fact in suspect.facts:
                fact_embedding = embedding_service.embed_fact(fact)
                fact_updates.append({
                    "scenario_id": scenario_id,
                    "suspect_id": suspect.suspect_id,
                    "fact_id": fact.fact_id,
                    "embedding": fact_embedding
                })

        if suspect_updates:
            await db.execute(update(Suspect), suspect_updates)

        if fact_updates:
            await db.execute(update(Fact), fact_updates)

        return {
            "suspects": len(suspect_updates),
            "facts": len(fact_updates),
        }


class ClueIndexer(BaseIndexer):
    """Indexer for clues."""

    async def index(
        self,
        db: AsyncSession,
        scenario_id: int,
        embedding_service: EmbeddingService
    ) -> Dict[str, int]:
        """Index all clues in a scenario."""
        loc_result = await db.execute(
            select(Location).where(Location.scenario_id == scenario_id)
        )
        loc_map = {loc.location_id: loc.name for loc in loc_result.scalars().all()}

        result = await db.execute(
            select(Clue).where(Clue.scenario_id == scenario_id)
        )
        clues = result.scalars().all()

        clue_updates = []
        for clue in clues:
            loc_name = loc_map.get(clue.location_id, "Unknown")
            description_embedding = embedding_service.embed_clue_description(
                name=clue.name, description=clue.description, found_at=loc_name
            )
            logic_embedding = embedding_service.embed_clue_logic(
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
            await db.execute(update(Clue), clue_updates)

        return {"clues": len(clue_updates)}


class ContextIndexer(BaseIndexer):
    """Indexer for scenario contexts (Facts with suspect_id=0)."""

    async def index(
        self,
        db: AsyncSession,
        scenario_id: int,
        embedding_service: EmbeddingService
    ) -> Dict[str, int]:
        """Index all context facts (suspect_id=0) in a scenario."""
        result = await db.execute(
            select(Fact).where(
                Fact.scenario_id == scenario_id,
                Fact.suspect_id == 0  # Context indicator
            )
        )
        contexts = result.scalars().all()

        context_updates = []
        for ctx in contexts:
            # Extract text from JSONB content
            content_text = ctx.content.get("text", str(ctx.content)) if isinstance(ctx.content, dict) else str(ctx.content)
            embedding = embedding_service.embed_text(content_text)
            context_updates.append({
                "scenario_id": scenario_id,
                "fact_id": ctx.fact_id,
                "embedding": embedding
            })

        if context_updates:
            await db.execute(update(Fact), context_updates)

        return {"contexts": len(context_updates)}


class RAGIndexer:
    """Generates and stores embeddings for scenario data.

    This service is responsible for:
    - Generating embeddings when scenarios are created
    - Updating embeddings when data changes
    - Storing chat message embeddings during conversations

    Uses Strategy Pattern with pluggable indexers for different entity types.
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        indexers: Optional[List[BaseIndexer]] = None
    ):
        """Initialize the RAG indexer.

        Parameters
        ----------
        embedding_service : EmbeddingService, optional
            The embedding service to use. Uses singleton if not provided.
        indexers : List[BaseIndexer], optional
            List of indexer strategies. Uses default indexers if not provided.
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self.indexers = indexers or [
            SuspectIndexer(),
            ClueIndexer(),
            ContextIndexer(),
        ]

    async def index_scenario(self, db: AsyncSession, scenario_id: int) -> Dict[str, Any]:
        """Index all data for a scenario.

        Generates and stores embeddings for all entities using registered indexers.

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
        stats: Dict[str, int] = {}

        for indexer in self.indexers:
            indexer_stats = await indexer.index(
                db, scenario_id, self.embedding_service
            )
            stats.update(indexer_stats)

        await db.commit()

        logger.info(f"Indexed scenario {scenario_id}: {stats}")
        return stats

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
