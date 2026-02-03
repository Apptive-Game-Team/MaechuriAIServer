"""Context builder for RAG - converts retrieved data to LLM-ready context."""
from typing import List, Optional, Any, Protocol, runtime_checkable, Dict
from dataclasses import dataclass
from abc import ABC, abstractmethod

from app.services.rag.retriever import (
    RetrievedFact,
    RetrievedClue,
    RetrievedChatMessage
)


# Header labels for context sections
SECTION_HEADERS: Dict[str, str] = {
    "scenario": "사건 정보",
    "clue": "관련 단서",
    "evidence": "관련 증거",
    "suspect": "관련 용의자",
    "suspect_info": "용의자 정보",
}


@runtime_checkable
class HasContent(Protocol):
    """Protocol for objects with content attribute."""
    content: str


@runtime_checkable
class HasNameDescription(Protocol):
    """Protocol for objects with name and description."""
    name: str
    description: str


@runtime_checkable
class HasSuspectProfile(Protocol):
    """Protocol for suspect-like objects."""
    name: str
    role: str
    age: int
    description: str
    alibi_summary: str


class EntityFormatter(ABC):
    """Abstract base class for entity formatters."""

    @abstractmethod
    def format(self, entity: Any) -> str:
        """Format a single entity to string."""
        pass

    def format_list(self, entities: List[Any]) -> str:
        """Format a list of entities."""
        if not entities:
            return ""
        return "\n".join(self.format(e) for e in entities)


class ScenarioContextFormatter(EntityFormatter):
    """Formatter for ScenarioContext entities."""

    def format(self, entity: HasContent) -> str:
        return entity.content


class ClueFormatter(EntityFormatter):
    """Formatter for Clue entities."""

    def format(self, entity: HasNameDescription) -> str:
        return f"- {entity.name}: {entity.description}"


class SuspectProfileFormatter(EntityFormatter):
    """Formatter for Suspect profile entities."""

    def format(self, entity: HasSuspectProfile) -> str:
        lines = [
            f"- {entity.name} ({entity.role}, {entity.age}세): {entity.description}",
            f"  알리바이: {entity.alibi_summary}"
        ]
        return "\n".join(lines)


class DetailedClueFormatter(EntityFormatter):
    """Formatter for detailed clue info (dict-based)."""

    def format(self, clue: dict) -> str:
        warning = "이 증거는 수사에 혼란을 줄 수 있음" if clue.get("is_red_herring") else ""
        return f"""[증거: {clue.get('name', '알 수 없음')}]
- 발견 장소: {clue.get('found_at', '알 수 없음')}
- 외관/설명: {clue.get('description', '설명 없음')}
- 해석된 의미: {clue.get('decoded_answer', '분석 결과 없음')}
- 주의: {warning}"""

    def format_list(self, clues: List[dict]) -> str:
        if not clues:
            return ""
        return "\n\n".join(self.format(c) for c in clues)


class SimpleHistoryFormatter(EntityFormatter):
    """Formatter for simple chat history (dict-based)."""

    def format(self, message: dict) -> str:
        return f"{message.get('role', 'unknown')}: {message.get('content', '')}"

    def format_list(self, messages: List[dict]) -> str:
        if not messages:
            return ""
        return "\n".join(self.format(m) for m in messages)


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
    Uses Strategy Pattern with pluggable formatters for different entity types.
    """

    def __init__(self):
        """Initialize with default formatters."""
        self._scenario_formatter = ScenarioContextFormatter()
        self._clue_formatter = ClueFormatter()
        self._suspect_formatter = SuspectProfileFormatter()
        self._detailed_clue_formatter = DetailedClueFormatter()
        self._simple_history_formatter = SimpleHistoryFormatter()

    @staticmethod
    def build_section(header_key: str, content: str) -> Optional[str]:
        """Build a context section with header if content exists.

        Parameters
        ----------
        header_key : str
            Key from SECTION_HEADERS (e.g., 'scenario', 'clue', 'suspect').
        content : str
            The content to wrap with the header.

        Returns
        -------
        Optional[str]
            Formatted section with header, or None if content is empty.
        """
        if not content:
            return None
        header = SECTION_HEADERS.get(header_key, header_key)
        return f"[{header}]\n{content}"

    @staticmethod
    def join_sections(*sections: Optional[str]) -> str:
        """Join non-empty sections with double newlines.

        Parameters
        ----------
        *sections : Optional[str]
            Variable number of section strings (can include None).

        Returns
        -------
        str
            Joined sections separated by double newlines.
        """
        return "\n\n".join(s for s in sections if s)

    def build_scenario_context(self, contexts: List[HasContent]) -> str:
        """Build formatted string from scenario contexts.

        Parameters
        ----------
        contexts : List[HasContent]
            ScenarioContext entities with content attribute.

        Returns
        -------
        str
            Formatted context string.
        """
        return self._scenario_formatter.format_list(contexts)

    def build_clue_summary(self, clues: List[HasNameDescription]) -> str:
        """Build formatted string from clues (simple name/description).

        Parameters
        ----------
        clues : List[HasNameDescription]
            Clue entities with name and description.

        Returns
        -------
        str
            Formatted clue summary.
        """
        return self._clue_formatter.format_list(clues)

    def build_suspect_profile(self, suspects: List[HasSuspectProfile]) -> str:
        """Build formatted string from suspect profiles.

        Parameters
        ----------
        suspects : List[HasSuspectProfile]
            Suspect entities with profile information.

        Returns
        -------
        str
            Formatted suspect profiles.
        """
        return self._suspect_formatter.format_list(suspects)

    def build_detailed_clue_context(
        self,
        clue_infos: Optional[List[dict]],
        empty_message: str = "(현재 분석 중인 증거 없음)"
    ) -> str:
        """Build detailed clue context from dict-based clue info.

        Parameters
        ----------
        clue_infos : List[dict], optional
            Clue info dicts with keys: name, found_at, description,
            decoded_answer, is_red_herring.
        empty_message : str, optional
            Message to return when clue_infos is empty.

        Returns
        -------
        str
            Formatted detailed clue context.
        """
        if not clue_infos:
            return empty_message
        return self._detailed_clue_formatter.format_list(clue_infos)

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
