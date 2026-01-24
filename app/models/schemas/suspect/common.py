"""Common suspect schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field


class TimelineEntrySchema(BaseModel):
    """Timeline entry for suspect activity. Time format: 'HH:MM-HH:MM' (e.g., '14:00-15:00')."""
    time: str = Field(description="시간 범위 (예: '14:00-15:00')")
    location: str = Field(description="위치")
    activity: str = Field(description="활동 내용")
    can_prove: bool = Field(description="증명 가능 여부 (증인, CCTV 등)")
    witness: Optional[str] = Field(default=None, description="증인 (있다면)")


class SecretTierSchema(BaseModel):
    """Secret revealed at pressure threshold."""
    threshold: int = Field(ge=0, le=100, description="이 비밀이 공개되는 최소 pressure")
    content: str = Field(description="비밀 내용")
    trigger_clue_ids: List[int] = Field(
        default=[],
        description="이 단서 제시 시 threshold 무시하고 바로 공개"
    )


class PersonalitySchema(BaseModel):
    """Personality and speech patterns."""
    speech_style: str = Field(description="말투 스타일 (예: 존댓말, 반말, 차갑게, 친근하게)")
    emotional_tendency: str = Field(description="감정 성향 (예: 침착함, 쉽게 흥분, 방어적)")
    lying_pattern: str = Field(description="거짓말 패턴 (deflect/deny/partial_truth)")
