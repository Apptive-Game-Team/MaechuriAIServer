"""Suspect response schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field
from .common import PersonalitySchema, FactEntrySchema, TimelineContentSchema, SecretContentSchema, HeardContentSchema


class SuspectGenerationSchema(BaseModel):
    """Complete suspect information for API responses and game state."""
    # Basic info
    suspect_id: int = Field(description="용의자 고유 ID (1, 2, 3...)")
    name: str = Field(description="이름")
    role: str = Field(description="역할/직업")
    age: int = Field(description="나이")
    gender: str = Field(description="성별")
    description: str = Field(description="외모/특징 설명")

    # Core game info
    is_culprit: bool = Field(description="범인 여부")
    motive: Optional[str] = Field(default=None, description="범인인 경우 동기")
    alibi_summary: str = Field(description="알리바이 요약 (한 문장)")

    # Timeline
    timeline: List[FactEntrySchema[TimelineContentSchema]] = Field(description="시간대별 행적")

    # Secrets by pressure threshold (innocent: all type="secret";
    # culprit threshold 0/30 = type="secret", threshold 50/70/90 = type="hidden")
    secrets: List[FactEntrySchema[SecretContentSchema]] = Field(
        description="Pressure-gated secrets (exactly 5: thresholds 0, 30, 50, 70, 90)."
    )

    # Second-hand information about other suspects (usually threshold=0)
    heard: List[FactEntrySchema[HeardContentSchema]] = Field(
        default_factory=list,
        description="2-4 facts this suspect heard or observed about other suspects (threshold=0)."
    )

    # Personality
    personality: PersonalitySchema = Field(description="성격 및 말투")

    # Image generation
    visual_description: Optional[str] = Field(default=None, description="이미지 생성을 위한 생김새 프롬프트 (영어)")


class SuspectGenerationListSchema(BaseModel):
    """List of suspects."""
    suspects: List[SuspectGenerationSchema]
