"""Scenario metadata schemas."""
from typing import Literal
from pydantic import BaseModel


class MetaSchema(BaseModel):
    """Scenario metadata including difficulty, theme, and tone."""
    difficulty: Literal["easy", "mid", "hard"]
    theme: str
    tone: str
    language: str = "ko"
