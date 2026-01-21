"""Context builder for RAG - converts retrieved data to LLM-ready context."""
from typing import List, Optional
from dataclasses import dataclass

from app.services.rag.retriever import (
    RetrievedTimeline,
    RetrievedSecret,
    RetrievedClue,
    RetrievedChatMessage
)


@dataclass
class RAGContext:
    """Container for RAG-retrieved context."""
    timelines: str
    secrets: str
    clues: str
    chat_history: str
    has_content: bool


class ContextBuilder:
    """Builds formatted context strings from retrieved RAG results.

    Converts retrieved data into formatted text suitable for LLM prompts.
    """

    def build_timeline_context(
        self,
        timelines: List[RetrievedTimeline],
        include_similarity: bool = False
    ) -> str:
        """Build context string from retrieved timelines.

        Parameters
        ----------
        timelines : List[RetrievedTimeline]
            Retrieved timeline entries.
        include_similarity : bool, optional
            Whether to include similarity scores. Defaults to False.

        Returns
        -------
        str
            Formatted timeline context.
        """
        if not timelines:
            return ""

        lines = ["[관련 행적 정보]"]
        for t in timelines:
            line = f"- {t.time_range}: {t.location}에서 {t.activity}"
            if t.can_prove:
                line += f" (증명 가능"
                if t.witness:
                    line += f", 목격자: {t.witness}"
                line += ")"
            if include_similarity:
                line += f" [유사도: {t.similarity:.2f}]"
            lines.append(line)

        return "\n".join(lines)

    def build_secret_context(
        self,
        secrets: List[RetrievedSecret],
        include_similarity: bool = False
    ) -> str:
        """Build context string from retrieved secrets.

        Parameters
        ----------
        secrets : List[RetrievedSecret]
            Retrieved secrets.
        include_similarity : bool, optional
            Whether to include similarity scores. Defaults to False.

        Returns
        -------
        str
            Formatted secret context.
        """
        if not secrets:
            return ""

        lines = ["[공개 가능한 비밀]"]
        for s in secrets:
            line = f"- (압박 {s.threshold}+) {s.content}"
            if include_similarity:
                line += f" [유사도: {s.similarity:.2f}]"
            lines.append(line)

        return "\n".join(lines)

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
        timelines: Optional[List[RetrievedTimeline]] = None,
        secrets: Optional[List[RetrievedSecret]] = None,
        clues: Optional[List[RetrievedClue]] = None,
        chat_history: Optional[List[RetrievedChatMessage]] = None,
        include_similarity: bool = False
    ) -> RAGContext:
        """Build complete RAG context from all retrieved data.

        Parameters
        ----------
        timelines : List[RetrievedTimeline], optional
            Retrieved timeline entries.
        secrets : List[RetrievedSecret], optional
            Retrieved secrets.
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
        timeline_ctx = self.build_timeline_context(timelines or [], include_similarity)
        secret_ctx = self.build_secret_context(secrets or [], include_similarity)
        clue_ctx = self.build_clue_context(clues or [], include_similarity=include_similarity)
        chat_ctx = self.build_chat_history_context(chat_history or [], include_similarity)

        has_content = any([timeline_ctx, secret_ctx, clue_ctx, chat_ctx])

        return RAGContext(
            timelines=timeline_ctx,
            secrets=secret_ctx,
            clues=clue_ctx,
            chat_history=chat_ctx,
            has_content=has_content
        )

    def build_suspect_interrogation_context(
        self,
        timelines: List[RetrievedTimeline],
        secrets: List[RetrievedSecret],
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

        timeline_ctx = self.build_timeline_context(timelines, include_similarity)
        if timeline_ctx:
            sections.append(timeline_ctx)

        secret_ctx = self.build_secret_context(secrets, include_similarity)
        if secret_ctx:
            sections.append(secret_ctx)

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
