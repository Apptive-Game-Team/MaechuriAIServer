"""RAG Service - Orchestrates retrieval and context building for agents."""
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass, field
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.retriever import RAGRetriever, get_rag_retriever, RetrievedChatMessage, RetrievedFact
from app.services.rag.context_builder import ContextBuilder, get_context_builder
from app.services.rag.indexer import RAGIndexer, get_rag_indexer


logger = logging.getLogger(__name__)


@dataclass
class SuspectRAGContext:
    """RAG context for suspect interrogation."""
    relevant_facts: str   # Formatted facts (within pressure threshold)
    relevant_history: str   # Formatted related past conversations
    full_context: str       # Combined context string
    retrieved_fact_ids: List[int] = field(default_factory=list)  # Fact IDs found relevant by similarity search


@dataclass
class ClueRAGContext:
    """RAG context for clue analysis."""
    related_clues: str      # Formatted related clues
    relevant_history: str   # Formatted related past conversations
    full_context: str       # Combined context string


@dataclass
class GeneralRAGContext:
    """RAG context for general detective chat."""
    scenario_context: str   # Incident, location, world info
    clue_context: str       # Related clues (if referenced)
    suspect_context: str    # Related suspect profiles (if referenced)
    relevant_history: str   # Relevant past conversations
    full_context: str       # Combined context string


@dataclass
class UnifiedRAGContext:
    """Unified RAG context that adapts based on chat mode.

    Supports general chat, clue analysis, and suspect inquiry modes.
    """
    full_context: str           # Combined context string
    relevant_history: str       # Formatted chat history
    mode: str                   # 'general', 'clue_analysis', 'suspect_inquiry'
    clue_details: Optional[dict] = None  # Clue info for analysis mode


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

    async def _get_history(
        self,
        db: AsyncSession,
        scenario_id: int,
        session_id: Optional[str],
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
        suspect_id: Optional[int] = None,
        clue_id: Optional[int] = None
    ) -> Tuple[List[RetrievedChatMessage], str]:
        """Retrieve chat history and format it.

        Returns
        -------
        Tuple[List[RetrievedChatMessage], str]
            (raw results, formatted string)
        """
        if not session_id:
            return [], ""

        history = await self.retriever.search_chat_history(
            db=db,
            scenario_id=scenario_id,
            session_id=session_id,
            query=query,
            top_k=top_k,
            threshold=threshold,
            suspect_id=suspect_id,
            clue_id=clue_id
        )
        history_str = self.context_builder.build_chat_history_context(history)
        return history, history_str

    async def get_suspect_context(
        self,
        db: AsyncSession,
        scenario_id: int,
        suspect_id: int,
        query: str,
        current_pressure: int,
        session_id: Optional[str] = None,
        suspect_names: Optional[dict] = None,
    ) -> SuspectRAGContext:
        """Get structured knowledge context for suspect interrogation.

        Uses the knowledge-partition approach: loads ALL accessible facts
        (threshold <= current_pressure) without semantic filtering, then
        builds a context partitioned by knowledge_type. Chat history uses
        a recency + semantic hybrid to preserve contradiction context.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        suspect_id : int
            The suspect ID.
        query : str
            The detective's current message (used for semantic history search).
        current_pressure : int
            Current pressure level (0-100).
        session_id : str, optional
            Session ID for history retrieval.
        suspect_names : dict, optional
            {suspect_id: name} mapping for heard-fact display.

        Returns
        -------
        SuspectRAGContext
            Structured context ready for the SuspectActor prompt.
        """
        # Load ALL accessible facts (no semantic miss)
        facts = await self.retriever.get_all_accessible_facts(
            db=db,
            scenario_id=scenario_id,
            suspect_id=suspect_id,
            current_pressure=current_pressure,
        )

        # Hybrid chat history: recency + semantic
        history: List[RetrievedChatMessage] = []
        if session_id:
            history = await self.retriever.search_chat_history_hybrid(
                db=db,
                scenario_id=scenario_id,
                session_id=session_id,
                query=query,
                suspect_id=suspect_id,
                recency_k=4,
                semantic_k=3,
                threshold=0.3,
            )

        full_context = self.context_builder.build_suspect_knowledge_context(
            facts=facts,
            chat_history=history,
            suspect_names=suspect_names or {},
        )

        return SuspectRAGContext(
            relevant_facts=full_context,
            relevant_history="",   # Merged into full_context above
            full_context=full_context,
            retrieved_fact_ids=[f.fact_id for f in facts]
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
        clues = await self.retriever.search_clues(
            db=db,
            scenario_id=scenario_id,
            query=query,
            top_k=top_k_clues,
            threshold=similarity_threshold,
            search_type="description"
        )
        clues = [c for c in clues if c.clue_id != clue_id]

        history, history_str = await self._get_history(
            db, scenario_id, session_id, query,
            top_k=top_k_history, threshold=similarity_threshold, clue_id=clue_id
        )

        clues_str = self.context_builder.build_clue_context(clues)
        full_context = self.context_builder.build_clue_analysis_context(
            clues=clues, chat_history=history
        )

        return ClueRAGContext(
            related_clues=clues_str,
            relevant_history=history_str,
            full_context=full_context
        )

    async def get_general_context(
        self,
        db: AsyncSession,
        scenario_id: int,
        query: str,
        session_id: Optional[str] = None,
        clue_ids: Optional[list[int]] = None,
        suspect_ids: Optional[list[int]] = None,
        top_k_context: int = 5,
        top_k_clues: int = 2,
        top_k_suspects: int = 2,
        top_k_history: int = 5,
        similarity_threshold: float = 0.3
    ) -> GeneralRAGContext:
        """Get RAG context for general detective chat.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        query : str
            The user's query/message.
        session_id : str, optional
            Session ID for history search.
        clue_ids : list[int], optional
            Specific clue IDs referenced in the message.
        suspect_ids : list[int], optional
            Specific suspect IDs referenced in the message.
        top_k_context : int, optional
            Number of scenario contexts to retrieve. Defaults to 5.
        top_k_clues : int, optional
            Number of clues to retrieve per referenced clue. Defaults to 2.
        top_k_suspects : int, optional
            Number of suspect profiles to retrieve. Defaults to 2.
        top_k_history : int, optional
            Number of history messages to retrieve. Defaults to 5.
        similarity_threshold : float, optional
            Minimum similarity threshold. Defaults to 0.3.

        Returns
        -------
        GeneralRAGContext
            Context containing relevant information.
        """
        contexts = await self.retriever.search_contexts(
            db=db, scenario_id=scenario_id, query=query,
            top_k=top_k_context, threshold=similarity_threshold
        )

        clues = []
        if clue_ids:
            clues = await self.retriever.search_clues(
                db=db, scenario_id=scenario_id, query=query,
                top_k=top_k_clues * len(clue_ids),
                threshold=similarity_threshold, search_type="description"
            )
            clues = [c for c in clues if c.clue_id in clue_ids]

        suspects = []
        if suspect_ids:
            suspects = await self.retriever.search_suspect_profiles(
                db=db, scenario_id=scenario_id, query=query,
                top_k=top_k_suspects, threshold=similarity_threshold,
                suspect_ids=suspect_ids
            )

        _, history_str = await self._get_history(
            db, scenario_id, session_id, query,
            top_k=top_k_history, threshold=similarity_threshold
        )

        scenario_context_str = self.context_builder.build_scenario_context(contexts)
        clue_context_str = self.context_builder.build_clue_summary(clues)
        suspect_context_str = self.context_builder.build_suspect_profile(suspects)

        full_context = ContextBuilder.join_sections(
            ContextBuilder.build_section("scenario", scenario_context_str),
            ContextBuilder.build_section("clue", clue_context_str),
            ContextBuilder.build_section("suspect", suspect_context_str),
        )

        return GeneralRAGContext(
            scenario_context=scenario_context_str,
            clue_context=clue_context_str,
            suspect_context=suspect_context_str,
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

    async def index_chat_messages_batch(
        self,
        db: AsyncSession,
        scenario_id: int,
        session_id: str,
        messages: list[dict],
        suspect_id: Optional[int] = None,
        clue_id: Optional[int] = None,
        context: str = ""
    ) -> list[int]:
        """Index multiple chat messages in a single batch (one embedding forward pass).

        Parameters
        ----------
        db : AsyncSession
            Database session.
        scenario_id : int
            The scenario ID.
        session_id : str
            Unique session identifier.
        messages : list[dict]
            List of dicts with 'role', 'content', and 'message_index' keys.
        suspect_id : int, optional
            Suspect ID if suspect chat.
        clue_id : int, optional
            Clue ID if clue chat.
        context : str, optional
            Additional context for embedding.

        Returns
        -------
        list[int]
            List of created message embedding IDs.
        """
        return await self.indexer.index_chat_messages_batch(
            db=db,
            scenario_id=scenario_id,
            session_id=session_id,
            messages=messages,
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
