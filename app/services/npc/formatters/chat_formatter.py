"""Formatter functions for chat service."""
from typing import List

from app.models.schemas.suspect import SuspectSchema, FactSchema


class ChatFormatter:
    """Formatter class for chat-related text formatting."""

    @staticmethod
    def format_suspect_summary(suspect: SuspectSchema) -> str:
        """Create suspect summary for Judge.

        Args:
            suspect: Suspect schema object

        Returns:
            Formatted summary string
        """
        culprit_str = "범인" if suspect.is_culprit else "무고한 용의자"
        return f"이름: {suspect.name}, 역할: {suspect.role}, 상태: {culprit_str}"

    @staticmethod
    def format_facts(facts: List[FactSchema]) -> str:
        """Build context string from facts list.

        Args:
            facts: List of fact schemas

        Returns:
            Formatted facts string
        """
        if not facts:
            return ""

        lines = ["[관련 사실]"]
        for fact in facts:
            text = None
            match fact.type:
                case "timeline":
                    text = ChatFormatter.format_timeline(fact.content)
                case "secret":
                    text = ChatFormatter.format_secret(fact)
                case _:
                    text = fact.content.to_string() if hasattr(fact.content, 'to_string') else str(fact.content)
            lines.append(text)

        return "\n".join(lines)

    @staticmethod
    def format_timeline(timeline: dict) -> str:
        """Format timeline dict to string.

        Args:
            timeline: Timeline content dict with time, location, activity

        Returns:
            Formatted timeline string
        """
        time = timeline.get("time")
        location = timeline.get("location")
        activity = timeline.get("activity")

        if time is None or location is None or activity is None:
            # Fallback: show the raw timeline content if expected keys are missing
            return f"- {str(timeline)}"

        return f"- {time}: {location}에서 {activity}"

    @staticmethod
    def format_secret(fact: FactSchema) -> str:
        """Format secret fact to string.

        Args:
            fact: Fact schema with secret content

        Returns:
            Formatted secret string
        """
        content = fact.content.get("content")

        if content is None:
            # Fallback: show the raw fact content if expected key is missing
            return f"- (압박 {fact.threshold}+) {str(fact.content)}"

        return f"- (압박 {fact.threshold}+) {content}"
