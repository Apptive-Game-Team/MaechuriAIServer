"""Common suspect schemas."""
from typing import Any

from pydantic import BaseModel, Field

class FactEntrySchema[T](BaseModel):
    """Fact entry schema."""
    fact_id: int = Field()
    threshold: int = Field(ge=0, le=100, description="이 사실이 공개되는 최소 pressure")
    content: T = Field(description="사실 내용")

class TimelineContentSchema(BaseModel):
    """Timeline entry for suspect activity. Time format: 'HH:MM-HH:MM' (e.g., '14:00-15:00')."""
    time: str = Field(description="시간 범위 (예: '14:00-15:00')")
    location: str = Field(description="위치")
    activity: str = Field(description="활동 내용")


class SecretContentSchema(BaseModel):
    """Secret revealed at pressure threshold."""
    content: str = Field(description="비밀 내용")


class PersonalitySchema(BaseModel):
    """Personality and speech patterns."""
    speech_style: str = Field(description="말투 스타일 (예: 존댓말, 반말, 차갑게, 친근하게)")
    emotional_tendency: str = Field(description="감정 성향 (예: 침착함, 쉽게 흥분, 방어적)")
    lying_pattern: str = Field(description="거짓말 패턴 (deflect/deny/partial_truth)")

class FactSchema(BaseModel):
    """Fact entry schema."""
    fact_id: int = Field()
    threshold: int = Field(ge=0, le=100, description="이 사실이 공개되는 최소 pressure")
    content: Any = Field(description="사실 내용")
    type: str = Field(description="사실의 종류 (예: timeline, secret)")

    @classmethod
    def from_timeline(
            cls,
            fact: FactEntrySchema["TimelineContentSchema"]
    ) -> "FactSchema":
        return cls(
            fact_id=fact.fact_id,
            threshold=fact.threshold,
            content=fact.content,
            type="timeline",
        )

    @classmethod
    def from_secret(
            cls,
            fact: FactEntrySchema["SecretContentSchema"]
    ) -> "FactSchema":
        return cls(
            fact_id=fact.fact_id,
            threshold=fact.threshold,
            content=fact.content,
            type="secret",
        )