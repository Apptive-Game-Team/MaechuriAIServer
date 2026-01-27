"""RAG Retriever for semantic search over embeddings."""
from typing import List, Optional, Any
from dataclasses import dataclass
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Suspect, Fact, Clue, ChatMessageEmbedding
from app.services.embedding import get_embedding_service, EmbeddingService
from app.api.dependencies import get_scenario_repository


logger = logging.getLogger(__name__)

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
    related_fact_ids: List[int]
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


class RAGRetriever:
    """Performs semantic search over embedded data.

    This service handles:
    - Finding relevant timeline entries based on user queries
    - Finding relevant secrets based on user queries
    - Finding relevant clues based on user queries
    - Finding relevant chat history based on user queries
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """Initialize the RAG retriever.

        Parameters
        ----------
        embedding_service : EmbeddingService, optional
            The embedding service to use. Uses singleton if not provided.
        """
        self.embedding_service = embedding_service or get_embedding_service()

    async def search_facts(
            self,
            db: AsyncSession,
            scenario_id: int,
            suspect_id: int,
            query: str,
            current_pressure: int = 0.1,
            top_k: int = 3,
            threshold: float = 0.1
    ) -> List[RetrievedFact]:
        """Search for relevant facts that can be revealed."""
        query_embedding = self.embedding_service.embed_query(query)

        suspect_result = await db.execute(
            select(Suspect.name).where(
                Suspect.scenario_id == scenario_id,
                Suspect.suspect_id == suspect_id
            )
        )

        suspect_name = suspect_result.scalar_one_or_none() or "Unknown"

        distance_expr = Fact.embedding.cosine_distance(query_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        stmt = (
            select(Fact, similarity_expr)
            .where(Fact.scenario_id == scenario_id)
            .where(Fact.suspect_id == suspect_id)
            .where(Fact.threshold <= current_pressure)
            .where(Fact.embedding.is_not(None))
            .order_by(distance_expr)
            .limit(top_k)
        )

        result = await db.execute(stmt)

        facts: List[RetrievedFact] = []
        for row in result:
            fact: Fact = row[0]
            similarity: float = row[1]
            
            if similarity >= threshold:
                facts.append(RetrievedFact(
                    suspect_id=suspect_id,
                    suspect_name=suspect_name,
                    fact_id=fact.fact_id,
                    threshold=fact.threshold,
                    content=fact.content,
                    type=fact.type,
                    similarity=similarity
                ))

        return facts

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
        query_embedding = self.embedding_service.embed_query(query)

        # Select embedding column based on search_type
        if search_type == "description":
            embedding_col = Clue.description_embedding
        else:
            embedding_col = Clue.logic_embedding

        distance_expr = embedding_col.cosine_distance(query_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        stmt = (
            select(Clue, similarity_expr)
            .where(Clue.scenario_id == scenario_id)
            .where(embedding_col.is_not(None))
            .order_by(distance_expr)
            .limit(top_k)
        )

        result = await db.execute(stmt)

        clues = []

        location_dict = await get_scenario_repository().get_location_dict(scenario_id)

        for row in result:
            clue: Clue = row[0]
            similarity: float = row[1]

            if similarity >= threshold:
                clues.append(RetrievedClue(
                    clue_id=clue.clue_id,
                    name=clue.name,
                    found_at=location_dict[clue.location_id],
                    description=clue.description,
                    logic_explanation=clue.logic_explanation,
                    decoded_answer=clue.decoded_answer,
                    is_red_herring=clue.is_red_herring,
                    related_fact_ids=clue.related_fact_ids or [],
                    similarity=similarity
                ))

        return clues

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
        query_embedding = self.embedding_service.embed_query(query)

        distance_expr = ChatMessageEmbedding.embedding.cosine_distance(query_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        stmt = (
            select(ChatMessageEmbedding, similarity_expr)
            .where(ChatMessageEmbedding.scenario_id == scenario_id)
            .where(ChatMessageEmbedding.session_id == session_id)
            .where(ChatMessageEmbedding.embedding.is_not(None))
        )

        if suspect_id is not None:
            stmt = stmt.where(ChatMessageEmbedding.suspect_id == suspect_id)
        
        if clue_id is not None:
            stmt = stmt.where(ChatMessageEmbedding.clue_id == clue_id)

        stmt = stmt.order_by(distance_expr).limit(top_k)

        result = await db.execute(stmt)

        messages = []
        for row in result:
            msg: ChatMessageEmbedding = row[0]
            similarity: float = row[1]

            if similarity >= threshold:
                messages.append(RetrievedChatMessage(
                    id=msg.id,
                    session_id=msg.session_id,
                    message_index=msg.message_index,
                    role=msg.role,
                    content=msg.content,
                    suspect_id=msg.suspect_id,
                    clue_id=msg.clue_id,
                    similarity=similarity
                ))

        return messages

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
        query_embedding = self.embedding_service.embed_query(query)

        distance_expr = ChatMessageEmbedding.embedding.cosine_distance(query_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        stmt = (
            select(ChatMessageEmbedding, similarity_expr)
            .where(ChatMessageEmbedding.scenario_id == scenario_id)
            .where(ChatMessageEmbedding.embedding.is_not(None))
        )

        if suspect_id is not None:
            stmt = stmt.where(ChatMessageEmbedding.suspect_id == suspect_id)

        stmt = stmt.order_by(distance_expr).limit(top_k)

        result = await db.execute(stmt)

        messages = []
        for row in result:
            msg: ChatMessageEmbedding = row[0]
            similarity: float = row[1]

            if similarity >= threshold:
                messages.append(RetrievedChatMessage(
                    id=msg.id,
                    session_id=msg.session_id,
                    message_index=msg.message_index,
                    role=msg.role,
                    content=msg.content,
                    suspect_id=msg.suspect_id,
                    clue_id=msg.clue_id,
                    similarity=similarity
                ))

        return messages


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