"""RAG Service - Orchestrates retrieval and context building for agents."""
from typing import Optional
from dataclasses import dataclass
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.retriever import RAGRetriever, get_rag_retriever
from app.services.rag.context_builder import ContextBuilder, get_context_builder
from app.services.rag.indexer import RAGIndexer, get_rag_indexer


logger = logging.getLogger(__name__)


@dataclass
class SuspectRAGContext:
    """RAG context for suspect interrogation."""
    relevant_facts: str   # Formatted facts (within pressure threshold)
    relevant_history: str   # Formatted related past conversations
    full_context: str       # Combined context string


@dataclass
class ClueRAGContext:
    """RAG context for clue analysis."""
    related_clues: str      # Formatted related clues
    relevant_history: str   # Formatted related past conversations
    full_context: str       # Combined context string


class RAGService:
    """High-level RAG service that orchestrates retrieval for agents.

    This service provides simplified methods for agents to get
    relevant context based on user queries.
    """

    def __init__(
        self,
        retriever: Optional[RAGRetriever] = None,
        context_builder: Optional[ContextBuilder] = None,
        indexer: Optional[RAGIndexer] = None
    ):
        """Initialize the RAG service.

        Parameters
        ----------
        retriever : RAGRetriever, optional
            The retriever to use. Uses singleton if not provided.
        context_builder : ContextBuilder, optional
            The context builder to use. Uses singleton if not provided.
        indexer : RAGIndexer, optional
            The indexer to use. Uses singleton if not provided.
        """
        self.retriever = retriever or get_rag_retriever()
        self.context_builder = context_builder or get_context_builder()
        self.indexer = indexer or get_rag_indexer()

    async def get_suspect_context(
        self,
        db: AsyncSession,
        scenario_id: int,
        suspect_id: int,
        query: str,
        current_pressure: int,
        session_id: Optional[str] = None,
        top_k_timeline: int = 3,
        top_k_secrets: int = 2,
        top_k_history: int = 5,
        similarity_threshold: float = 0.5
    ) -> SuspectRAGContext:
        """Get RAG context for suspect interrogation.

        Retrieves relevant timeline entries, secrets, and chat history
        based on the user's query.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        suspect_id : int
            The suspect ID.
        query : str
            The user's query/message.
        current_pressure : int
            Current pressure level (0-100).
        session_id : str, optional
            Session ID for history search.
        top_k_timeline : int, optional
            Number of timeline entries to retrieve. Defaults to 3.
        top_k_secrets : int, optional
            Number of secrets to retrieve. Defaults to 2.
        top_k_history : int, optional
            Number of history messages to retrieve. Defaults to 5.
        similarity_threshold : float, optional
            Minimum similarity threshold. Defaults to 0.5.

        Returns
        -------
        SuspectRAGContext
            Context containing relevant information.
        """

        # Retrieve relevant facts (only those within pressure threshold)
        facts = await self.retriever.search_facts(
            db=db,
            scenario_id=scenario_id,
            suspect_id=suspect_id,
            query=query,
            current_pressure=current_pressure,
            top_k=top_k_secrets,
            threshold=similarity_threshold
        )

        # Retrieve relevant chat history
        history = []
        if session_id:
            history = await self.retriever.search_chat_history(
                db=db,
                scenario_id=scenario_id,
                session_id=session_id,
                query=query,
                top_k=top_k_history,
                threshold=similarity_threshold,
                suspect_id=suspect_id
            )

        # Build context strings
        fact_str = self.context_builder.build_fact_context(facts)
        history_str = self.context_builder.build_chat_history_context(history)

        full_context = self.context_builder.build_suspect_interrogation_context(
            facts=facts,
            chat_history=history
        )

        return SuspectRAGContext(
            relevant_facts=fact_str,
            relevant_history=history_str,
            full_context=full_context
        )

    async def get_clue_context(
        self,
        db: AsyncSession,
        scenario_id: int,
        clue_id: int,
        query: str,
        session_id: Optional[str] = None,
        top_k_clues: int = 2,
        top_k_history: int = 5,
        similarity_threshold: float = 0.5
    ) -> ClueRAGContext:
        """Get RAG context for clue analysis.

        Retrieves related clues and relevant chat history.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        clue_id : int
            The current clue ID being analyzed.
        query : str
            The user's query/message.
        session_id : str, optional
            Session ID for history search.
        top_k_clues : int, optional
            Number of related clues to retrieve. Defaults to 2.
        top_k_history : int, optional
            Number of history messages to retrieve. Defaults to 5.
        similarity_threshold : float, optional
            Minimum similarity threshold. Defaults to 0.5.

        Returns
        -------
        ClueRAGContext
            Context containing relevant information.
        """
        # Retrieve related clues
        clues = await self.retriever.search_clues(
            db=db,
            scenario_id=scenario_id,
            query=query,
            top_k=top_k_clues,
            threshold=similarity_threshold,
            search_type="description"
        )

        # Filter out the current clue from results
        clues = [c for c in clues if c.clue_id != clue_id]

        # Retrieve relevant chat history
        history = []
        if session_id:
            history = await self.retriever.search_chat_history(
                db=db,
                scenario_id=scenario_id,
                session_id=session_id,
                query=query,
                top_k=top_k_history,
                threshold=similarity_threshold,
                clue_id=clue_id
            )

        # Build context strings
        clues_str = self.context_builder.build_clue_context(clues)
        history_str = self.context_builder.build_chat_history_context(history)

        full_context = self.context_builder.build_clue_analysis_context(
            clues=clues,
            chat_history=history
        )

        return ClueRAGContext(
            related_clues=clues_str,
            relevant_history=history_str,
            full_context=full_context
        )

    async def index_scenario(self, db: AsyncSession, scenario_id: int) -> dict:
        """Index all data for a scenario.

        Should be called after scenario generation to enable RAG.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID to index.

        Returns
        -------
        dict
            Indexing statistics.
        """
        return await self.indexer.index_scenario(db, scenario_id)

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
        context: str = ""
    ) -> int:
        """Index a chat message for future retrieval.

        Should be called after each message exchange.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        session_id : str
            Unique session identifier.
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
        return await self.indexer.index_chat_message(
            db=db,
            scenario_id=scenario_id,
            session_id=session_id,
            message_index=message_index,
            role=role,
            content=content,
            suspect_id=suspect_id,
            clue_id=clue_id,
            context=context
        )


# Singleton instance
_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get the singleton RAG service instance.

    Returns
    -------
    RAGService
        The RAG service instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = RAGService()
    return _service_instance
