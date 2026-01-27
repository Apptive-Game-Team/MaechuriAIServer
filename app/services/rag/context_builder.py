"""Context builder for RAG - converts retrieved data to LLM-ready context."""
from typing import List, Optional
from dataclasses import dataclass

from app.services.rag.retriever import (
    RetrievedFact,
    RetrievedClue,
    RetrievedChatMessage
)

@dataclass
class RAGContext:
    """Container for RAG-retrieved context."""
    facts: str
    clues: str
    chat_history: str
    has_content: bool


class ContextBuilder:
    """Builds formatted context strings from retrieved RAG results.

    Converts retrieved data into formatted text suitable for LLM prompts.
    """

    def build_fact_context(
        self,
        facts: List[RetrievedFact],
        include_similarity: bool = False
    ) -> str:
        """Build context string from retrieved facts."""
        if not facts:
            return ""

        lines = ["[관련 사실]"]
        for fact in facts:
            text = None
            match fact.type:
                case "timeline":
                    text = self._build_timeline_context(fact.content)
                case "secret":
                    text = self._build_secret_context(fact)
                case _:
                    text = fact.content.to_string()
            if include_similarity:
                text += f" [유사도: {fact.similarity:.2f}]"
            lines.append(text)

        return "\n".join(lines)

    def _build_timeline_context(
        self,
        timeline: dict,
    ) -> str:
        time = timeline.get("time")
        location = timeline.get("location")
        activity = timeline.get("activity")

        if time is None or location is None or activity is None:
            # Fallback: show the raw timeline content if expected keys are missing
            return f"- {str(timeline)}"

        return f"- {time}: {location}에서 {activity}"
    def _build_secret_context(
        self,
        fact: RetrievedFact
    ) -> str:
        content = fact.content.get("content")
        
        if content is None:
            # Fallback: show the raw fact content if expected key is missing
            return f"- (압박 {fact.threshold}+) {str(fact.content)}"
        
        return f"- (압박 {fact.threshold}+) {content}"

    def build_clue_context(
        self,
        clues: List[RetrievedClue],
        include_logic: bool = True,
        include_similarity: bool = False
    ) -> str:
        """Build context string from retrieved clues.

        Parameters
        ----------
        clues : List[RetrievedClue]
            Retrieved clues.
        include_logic : bool, optional
            Whether to include logic explanation. Defaults to True.
        include_similarity : bool, optional
            Whether to include similarity scores. Defaults to False.

        Returns
        -------
        str
            Formatted clue context.
        """
        if not clues:
            return ""

        lines = ["[관련 증거 정보]"]
        for c in clues:
            line = f"- {c.name} (발견: {c.found_at}): {c.description}"
            if include_logic and c.logic_explanation:
                line += f"\n  분석: {c.logic_explanation}"
            if c.is_red_herring:
                line += " [주의: 함정 증거 가능성]"
            if include_similarity:
                line += f" [유사도: {c.similarity:.2f}]"
            lines.append(line)

        return "\n".join(lines)

    def build_chat_history_context(
        self,
        messages: List[RetrievedChatMessage],
        include_similarity: bool = False
    ) -> str:
        """Build context string from retrieved chat messages.

        Parameters
        ----------
        messages : List[RetrievedChatMessage]
            Retrieved chat messages.
        include_similarity : bool, optional
            Whether to include similarity scores. Defaults to False.

        Returns
        -------
        str
            Formatted chat history context.
        """
        if not messages:
            return ""

        # Sort by message_index to maintain conversation order
        sorted_messages = sorted(messages, key=lambda m: m.message_index)

        role_map = {"user": "탐정", "detective": "탐정", "suspect": "용의자"}

        lines = ["[관련 이전 대화]"]
        for m in sorted_messages:
            role_label = role_map.get(m.role, m.role)
            line = f"- {role_label}: {m.content}"
            if include_similarity:
                line += f" [유사도: {m.similarity:.2f}]"
            lines.append(line)

        return "\n".join(lines)

    def build_full_context(
        self,
        facts: Optional[List[RetrievedFact]] = None,
        clues: Optional[List[RetrievedClue]] = None,
        chat_history: Optional[List[RetrievedChatMessage]] = None,
        include_similarity: bool = False
    ) -> RAGContext:
        """Build complete RAG context from all retrieved data.

        Parameters
        ----------
        facts : List[RetrievedFact], optional
            Retrieved facts.
        clues : List[RetrievedClue], optional
            Retrieved clues.
        chat_history : List[RetrievedChatMessage], optional
            Retrieved chat messages.
        include_similarity : bool, optional
            Whether to include similarity scores. Defaults to False.

        Returns
        -------
        RAGContext
            Container with all formatted context strings.
        """
        facts_ctx = self.build_fact_context(facts or [], include_similarity)
        clue_ctx = self.build_clue_context(clues or [], include_similarity=include_similarity)
        chat_ctx = self.build_chat_history_context(chat_history or [], include_similarity)

        has_content = any([facts_ctx, clue_ctx, chat_ctx])

        return RAGContext(
            facts=facts_ctx,
            clues=clue_ctx,
            chat_history=chat_ctx,
            has_content=has_content
        )

    def build_suspect_interrogation_context(
        self,
        facts: List[RetrievedFact],
        chat_history: List[RetrievedChatMessage],
        include_similarity: bool = False
    ) -> str:
        """Build context specifically for suspect interrogation.

        Combines timelines, secrets, and chat history into a single
        context string optimized for the suspect actor.

        Parameters
        ----------
        timelines : List[RetrievedTimeline]
            Retrieved timeline entries.
        secrets : List[RetrievedSecret]
            Retrieved secrets.
        chat_history : List[RetrievedChatMessage]
            Retrieved chat messages.
        include_similarity : bool, optional
            Whether to include similarity scores. Defaults to False.

        Returns
        -------
        str
            Combined context string.
        """
        sections = []

        fact_ctx = self.build_fact_context(facts, include_similarity)
        if fact_ctx:
            sections.append(fact_ctx)

        chat_ctx = self.build_chat_history_context(chat_history, include_similarity)
        if chat_ctx:
            sections.append(chat_ctx)

        if not sections:
            return ""

        return "\n\n".join(sections)

    def build_clue_analysis_context(
        self,
        clues: List[RetrievedClue],
        chat_history: List[RetrievedChatMessage],
        include_similarity: bool = False
    ) -> str:
        """Build context specifically for clue analysis.

        Combines clue information and chat history for the clue agent.

        Parameters
        ----------
        clues : List[RetrievedClue]
            Retrieved clues.
        chat_history : List[RetrievedChatMessage]
            Retrieved chat messages.
        include_similarity : bool, optional
            Whether to include similarity scores. Defaults to False.

        Returns
        -------
        str
            Combined context string.
        """
        sections = []

        clue_ctx = self.build_clue_context(clues, include_logic=True, include_similarity=include_similarity)
        if clue_ctx:
            sections.append(clue_ctx)

        chat_ctx = self.build_chat_history_context(chat_history, include_similarity)
        if chat_ctx:
            sections.append(chat_ctx)

        if not sections:
            return ""

        return "\n\n".join(sections)


# Singleton instance
_builder_instance: Optional[ContextBuilder] = None


def get_context_builder() -> ContextBuilder:
    """Get the singleton context builder instance.

    Returns
    -------
    ContextBuilder
        The context builder instance.
    """
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = ContextBuilder()
    return _builder_instance
