"""Suspect response schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field
from .common import TimelineEntrySchema, SecretTierSchema, PersonalitySchema


class SuspectSchema(BaseModel):
    """Complete suspect information."""
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
    timeline: List[TimelineEntrySchema] = Field(description="시간대별 행적")

    # Secrets by pressure threshold
    secrets: List[SecretTierSchema] = Field(
        description="pressure threshold 순으로 정렬된 비밀 목록 (최소 5개: 0, 30, 50, 70, 90)"
    )

    # Personality
    personality: PersonalitySchema = Field(description="성격 및 말투")

    # Critical evidence for confession
    critical_evidence_ids: List[int] = Field(
        default=[],
        description="모두 제시 시 자백 유도 가능한 핵심 증거 ID들"
    )


class SuspectListSchema(BaseModel):
    """List of suspects."""
    suspects: List[SuspectSchema]
