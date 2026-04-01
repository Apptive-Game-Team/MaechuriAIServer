"""RAG Retriever for semantic search over embeddings."""
from typing import List, Optional, Any, TypeVar, Callable, Type
from dataclasses import dataclass
import logging

from sqlalchemy import select, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from app.db.models import Suspect, Fact, Clue, ChatMessageEmbedding
from app.services.embedding import get_embedding_service, EmbeddingService


logger = logging.getLogger(__name__)

T = TypeVar("T")  # Result dataclass type
M = TypeVar("M")  # SQLAlchemy model type

@dataclass
class RetrievedFact:
    """Retrieved fact with similarity score."""
    suspect_id: int
    suspect_name: str
    fact_id: int
    threshold: int
    content: Any
    type: str
    similarity: float

@dataclass
class RetrievedClue:
    """Retrieved clue with similarity score."""
    clue_id: int
    name: str
    found_at: str
    description: str
    logic_explanation: str
    decoded_answer: Optional[str]
    is_red_herring: bool
    related_suspect_ids: List[int]
    similarity: float


@dataclass
class RetrievedChatMessage:
    """Retrieved chat message with similarity score."""
    id: int
    session_id: str
    message_index: int
    role: str
    content: str
    suspect_id: Optional[int]
    clue_id: Optional[int]
    similarity: float


@dataclass
class RetrievedSuspectProfile:
    """Retrieved suspect profile with similarity score."""
    suspect_id: int
    name: str
    role: str
    age: int
    gender: str
    description: str
    alibi_summary: str
    similarity: float


@dataclass
class RetrievedContext:
    """Retrieved scenario context with similarity score."""
    context_id: int
    type: str  # 'incident', 'location', 'world'
    content: str
    similarity: float


class RAGRetriever:
    """Performs semantic search over embedded data.

    This service handles:
    - Finding relevant timeline entries based on user queries
    - Finding relevant secrets based on user queries
    - Finding relevant clues based on user queries
    - Finding relevant chat history based on user queries

    Uses a generic search engine pattern internally to reduce code duplication.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """Initialize the RAG retriever.

        Parameters
        ----------
        embedding_service : EmbeddingService, optional
            The embedding service to use. Uses singleton if not provided.
        """
        self.embedding_service = embedding_service or get_embedding_service()

    async def _search(
        self,
        db: AsyncSession,
        query: str,
        model: Type[M],
        embedding_col: InstrumentedAttribute,
        mapper: Callable[[M, float], T],
        base_filters: List,
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[T]:
        """Generic search engine for semantic similarity search.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        query : str
            The search query.
        model : Type[M]
            SQLAlchemy model class to search.
        embedding_col : InstrumentedAttribute
            The embedding column to search against.
        mapper : Callable[[M, float], T]
            Function to convert (model_instance, similarity) to result dataclass.
        base_filters : List
            List of SQLAlchemy filter conditions.
        top_k : int
            Maximum number of results.
        threshold : float
            Minimum similarity threshold.

        Returns
        -------
        List[T]
            List of mapped results above threshold.
        """
        query_embedding = self.embedding_service.embed_query(query)

        distance_expr = embedding_col.cosine_distance(query_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        stmt = (
            select(model, similarity_expr)
            .where(embedding_col.is_not(None))
        )

        for condition in base_filters:
            stmt = stmt.where(condition)

        stmt = stmt.order_by(distance_expr).limit(top_k)

        result = await db.execute(stmt)

        return [
            mapper(row[0], row[1])
            for row in result
            if row[1] >= threshold
        ]

    @staticmethod
    def _map_chat_message(msg: "ChatMessageEmbedding", similarity: float = 1.0) -> RetrievedChatMessage:
        """Convert a ChatMessageEmbedding ORM row to a RetrievedChatMessage dataclass."""
        return RetrievedChatMessage(
            id=msg.id,
            session_id=msg.session_id,
            message_index=msg.message_index,
            role=msg.role,
            content=msg.content,
            suspect_id=msg.suspect_id,
            clue_id=msg.clue_id,
            similarity=similarity,
        )

    async def search_facts(
        self,
        db: AsyncSession,
        scenario_id: int,
        suspect_id: int,
        query: str,
        current_pressure: int = 0,
        top_k: int = 3,
        threshold: float = 0.1
    ) -> List[RetrievedFact]:
        """Search for relevant facts that can be revealed."""
        suspect_result = await db.execute(
            select(Suspect.name).where(
                Suspect.scenario_id == scenario_id,
                Suspect.suspect_id == suspect_id
            )
        )
        suspect_name = suspect_result.scalar_one_or_none() or "Unknown"

        def mapper(fact: Fact, similarity: float) -> RetrievedFact:
            return RetrievedFact(
                suspect_id=suspect_id,
                suspect_name=suspect_name,
                fact_id=fact.fact_id,
                threshold=fact.threshold,
                content=fact.content,
                type=fact.type,
                similarity=similarity
            )

        return await self._search(
            db=db,
            query=query,
            model=Fact,
            embedding_col=Fact.embedding,
            mapper=mapper,
            base_filters=[
                Fact.scenario_id == scenario_id,
                Fact.suspect_id == suspect_id,
                Fact.threshold <= current_pressure,
            ],
            top_k=top_k,
            threshold=threshold
        )


    async def get_all_accessible_facts(
        self,
        db: AsyncSession,
        scenario_id: int,
        suspect_id: int,
        current_pressure: int,
    ) -> list:
        """Return ALL suspect facts accessible at the current pressure level.

        Unlike search_facts(), this performs NO semantic filtering — it returns
        every fact whose threshold <= current_pressure, ensuring no facts are
        missed due to low embedding similarity. Used by the knowledge partition
        approach where the LLM receives complete, structured context.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        suspect_id : int
            The suspect ID (must be > 0).
        current_pressure : int
            Current pressure level (0-100). Only facts with threshold <= this
            value are returned.

        Returns
        -------
        List[RetrievedFact]
            All accessible facts ordered by threshold then fact_id.
        """
        stmt = (
            select(Fact)
            .where(
                Fact.scenario_id == scenario_id,
                Fact.suspect_id == suspect_id,
                Fact.threshold <= current_pressure,
            )
            .order_by(Fact.threshold.asc(), Fact.fact_id.asc())
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [
            RetrievedFact(
                suspect_id=suspect_id,
                suspect_name="",  # Name resolved upstream; not needed here
                fact_id=row.fact_id,
                threshold=row.threshold,
                content=row.content,
                type=row.type,
                similarity=1.0  # No semantic score; all are fully accessible
            )
            for row in rows
        ]

    async def search_chat_history_hybrid(
        self,
        db: AsyncSession,
        scenario_id: int,
        session_id: str,
        query: str,
        suspect_id: Optional[int] = None,
        clue_id: Optional[int] = None,
        recency_k: int = 4,
        semantic_k: int = 3,
        threshold: float = 0.3,
    ) -> list:
        """Retrieve chat history using a recency + semantic hybrid strategy.

        Always includes the most recent  messages to preserve
        contradiction context, then adds up to  semantically
        relevant older messages. Results are deduplicated and sorted
        chronologically by message_index.

        Parameters
        ----------
        recency_k : int
            Number of most-recent messages to always include. Defaults to 4.
        semantic_k : int
            Number of semantically similar older messages to include. Defaults to 3.
        threshold : float
            Minimum cosine similarity for semantic matches. Defaults to 0.3.
        """
        base_filters = [
            ChatMessageEmbedding.scenario_id == scenario_id,
            ChatMessageEmbedding.session_id == session_id,
        ]
        if suspect_id is not None:
            base_filters.append(ChatMessageEmbedding.suspect_id == suspect_id)
        if clue_id is not None:
            base_filters.append(ChatMessageEmbedding.clue_id == clue_id)

        # 1. Most recent messages (recency bias)
        recent_stmt = (
            select(ChatMessageEmbedding)
            .where(*base_filters)
            .order_by(ChatMessageEmbedding.message_index.desc())
            .limit(recency_k)
        )
        recent_rows = (await db.execute(recent_stmt)).scalars().all()
        recent_ids = {r.id for r in recent_rows}

        # 2. Semantic search on older messages (excluding recent ones)
        semantic_rows = []
        if query:
            query_embedding = self.embedding_service.embed_query(query)
            distance_expr = ChatMessageEmbedding.embedding.cosine_distance(query_embedding)
            semantic_stmt = (
                select(ChatMessageEmbedding)
                .where(
                    *base_filters,
                    ChatMessageEmbedding.id.notin_(recent_ids),
                    ChatMessageEmbedding.embedding.is_not(None),
                    (1 - distance_expr) >= threshold,
                )
                .order_by(distance_expr)
                .limit(semantic_k)
            )
            semantic_rows = (await db.execute(semantic_stmt)).scalars().all()

        # 3. Merge, deduplicate, sort chronologically
        all_rows = {r.id: r for r in list(recent_rows) + list(semantic_rows)}.values()
        sorted_rows = sorted(all_rows, key=lambda r: r.message_index)

        return [self._map_chat_message(r) for r in sorted_rows]

    async def search_clues(
        self,
        db: AsyncSession,
        scenario_id: int,
        query: str,
        top_k: int = 3,
        threshold: float = 0.5,
        search_type: str = "description"
    ) -> List[RetrievedClue]:
        """Search for relevant clues."""
        embedding_col = Clue.description_embedding if search_type == "description" else Clue.logic_embedding

        from app.api.dependencies import get_scenario_repository
        location_dict = await get_scenario_repository().get_location_dict(scenario_id)

        def mapper(clue: Clue, similarity: float) -> RetrievedClue:
            return RetrievedClue(
                clue_id=clue.clue_id,
                name=clue.name,
                found_at=location_dict.get(clue.location_id, "Unknown"),
                description=clue.description,
                logic_explanation=clue.logic_explanation,
                decoded_answer=clue.decoded_answer,
                is_red_herring=clue.is_red_herring,
                related_suspect_ids=clue.related_suspect_ids or [],
                similarity=similarity
            )

        return await self._search(
            db=db,
            query=query,
            model=Clue,
            embedding_col=embedding_col,
            mapper=mapper,
            base_filters=[Clue.scenario_id == scenario_id],
            top_k=top_k,
            threshold=threshold
        )

    async def search_chat_history(
        self,
        db: AsyncSession,
        scenario_id: int,
        session_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
        suspect_id: Optional[int] = None,
        clue_id: Optional[int] = None
    ) -> List[RetrievedChatMessage]:
        """Search for relevant chat messages in history."""
        mapper = self._map_chat_message

        filters = [
            ChatMessageEmbedding.scenario_id == scenario_id,
            ChatMessageEmbedding.session_id == session_id,
        ]
        if suspect_id is not None:
            filters.append(ChatMessageEmbedding.suspect_id == suspect_id)
        if clue_id is not None:
            filters.append(ChatMessageEmbedding.clue_id == clue_id)

        return await self._search(
            db=db,
            query=query,
            model=ChatMessageEmbedding,
            embedding_col=ChatMessageEmbedding.embedding,
            mapper=mapper,
            base_filters=filters,
            top_k=top_k,
            threshold=threshold
        )

    async def search_all_sessions_history(
        self,
        db: AsyncSession,
        scenario_id: int,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
        suspect_id: Optional[int] = None
    ) -> List[RetrievedChatMessage]:
        """Search for relevant chat messages across all sessions."""
        mapper = self._map_chat_message

        filters = [ChatMessageEmbedding.scenario_id == scenario_id]
        if suspect_id is not None:
            filters.append(ChatMessageEmbedding.suspect_id == suspect_id)

        return await self._search(
            db=db,
            query=query,
            model=ChatMessageEmbedding,
            embedding_col=ChatMessageEmbedding.embedding,
            mapper=mapper,
            base_filters=filters,
            top_k=top_k,
            threshold=threshold
        )

    async def search_suspect_profiles(
        self,
        db: AsyncSession,
        scenario_id: int,
        query: str,
        top_k: int = 3,
        threshold: float = 0.5,
        suspect_ids: Optional[List[int]] = None
    ) -> List[RetrievedSuspectProfile]:
        """Search for relevant suspect profiles based on query."""
        def mapper(suspect: Suspect, similarity: float) -> RetrievedSuspectProfile:
            return RetrievedSuspectProfile(
                suspect_id=suspect.suspect_id,
                name=suspect.name,
                role=suspect.role,
                age=suspect.age,
                gender=suspect.gender,
                description=suspect.description,
                alibi_summary=suspect.alibi_summary,
                similarity=similarity
            )

        filters = [Suspect.scenario_id == scenario_id]
        if suspect_ids:
            filters.append(Suspect.suspect_id.in_(suspect_ids))

        return await self._search(
            db=db,
            query=query,
            model=Suspect,
            embedding_col=Suspect.profile_embedding,
            mapper=mapper,
            base_filters=filters,
            top_k=top_k,
            threshold=threshold
        )

    async def search_contexts(
        self,
        db: AsyncSession,
        scenario_id: int,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
        context_types: Optional[List[str]] = None
    ) -> List[RetrievedContext]:
        """Search for relevant scenario contexts (Facts with suspect_id=0)."""
        def mapper(fact: Fact, similarity: float) -> RetrievedContext:
            # Extract text from JSONB content
            content = fact.content.get("text", str(fact.content)) if isinstance(fact.content, dict) else str(fact.content)
            return RetrievedContext(
                context_id=fact.fact_id,
                type=fact.type,
                content=content,
                similarity=similarity
            )

        filters = [
            Fact.scenario_id == scenario_id,
            Fact.suspect_id == 0,  # Context indicator
        ]
        if context_types:
            filters.append(Fact.type.in_(context_types))

        return await self._search(
            db=db,
            query=query,
            model=Fact,
            embedding_col=Fact.embedding,
            mapper=mapper,
            base_filters=filters,
            top_k=top_k,
            threshold=threshold
        )


# Singleton instance
_retriever_instance: Optional[RAGRetriever] = None


def get_rag_retriever() -> RAGRetriever:
    """Get the singleton RAG retriever instance.

    Returns
    -------
    RAGRetriever
        The RAG retriever instance.
    """
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = RAGRetriever()
    return _retriever_instance