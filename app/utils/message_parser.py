"""Utility functions for parsing user messages."""
import re
from typing import List, Tuple


class MessageParser:
    """Parser for extracting references from user messages."""

    @staticmethod
    def parse_references(message: str) -> Tuple[List[int], List[int]]:
        """Parse [c:01], [s:01] references from message.

        Args:
            message: User message text

        Returns:
            Tuple[List[int], List[int]]: (clue_ids, suspect_ids)
        """
        clue_ids: List[int] = []
        suspect_ids: List[int] = []

        # [c:01], [c:1], [C:01] pattern matching
        clue_pattern = r'\[c:(\d+)\]'
        suspect_pattern = r'\[s:(\d+)\]'

        # Case insensitive
        clue_matches = re.findall(clue_pattern, message, re.IGNORECASE)
        suspect_matches = re.findall(suspect_pattern, message, re.IGNORECASE)

        # Convert strings to integers
        clue_ids = [int(m) for m in clue_matches]
        suspect_ids = [int(m) for m in suspect_matches]

        return clue_ids, suspect_ids
