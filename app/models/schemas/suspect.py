from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from app.models.schemas.clue import ClueItemSchema
from app.models.schemas.scenario import (
    TimeRangeSchema,
    WorldContextSchema,
    GroundTruthSchema,
    ConstraintsSchema,
    SuspectGenConfig
)

if TYPE_CHECKING:
    from app.models.schemas.scenario import ScenarioExpansion

# === Sub Schemas ===

class TimelineEntrySchema(BaseModel):
    """시간대별 행적"""
    time: str = Field(description="시간 범위 (예: '14:00-15:00')")
    location: str = Field(description="위치")
    activity: str = Field(description="활동 내용")
    can_prove: bool = Field(description="증명 가능 여부 (증인, CCTV 등)")
    witness: Optional[str] = Field(default=None, description="증인 (있다면)")


class SecretTierSchema(BaseModel):
    """압박 구간별 비밀"""
    threshold: int = Field(ge=0, le=100, description="이 비밀이 공개되는 최소 pressure")
    content: str = Field(description="비밀 내용")
    trigger_evidence_ids: List[int] = Field(
        default=[],
        description="이 증거 제시 시 threshold 무시하고 바로 공개"
    )


class PersonalitySchema(BaseModel):
    """성격 및 말투"""
    speech_style: str = Field(description="말투 스타일 (예: 존댓말, 반말, 차갑게, 친근하게)")
    emotional_tendency: str = Field(description="감정 성향 (예: 침착함, 쉽게 흥분, 방어적)")
    lying_pattern: str = Field(description="거짓말 패턴 (deflect/deny/partial_truth)")


# === Request Schema ===

class CaseContextSchema(BaseModel):
    """사건 컨텍스트 (Suspect 생성 요청용)"""
    incident_time: TimeRangeSchema
    primary_location: str
    incident_type: str
    summary: str


class SuspectGenerationRequest(BaseModel):
    """Suspect 생성 요청"""
    case_context: CaseContextSchema
    world_context: WorldContextSchema
    ground_truth: GroundTruthSchema
    generation_config: SuspectGenConfig
    clues: List[ClueItemSchema] = []
    constraints: Optional[ConstraintsSchema] = None

    @classmethod
    def from_expansion(
        cls,
        expansion: ScenarioExpansion,
        clues: List[ClueItemSchema] = []
    ) -> SuspectGenerationRequest:
        """ScenarioExpansion에서 SuspectGenerationRequest 생성"""
        return cls(
            case_context=CaseContextSchema(
                incident_time=expansion.incident.time_range,
                primary_location=expansion.incident.location,
                incident_type=expansion.incident.type,
                summary=expansion.incident.summary
            ),
            world_context=expansion.world_detail,
            ground_truth=expansion.ground_truth_detail,
            generation_config=expansion.generation_targets.suspects,
            clues=clues,
            constraints=expansion.constraints
        )


# === Main Suspect Schema ===

class SuspectSchema(BaseModel):
    """용의자 전체 정보"""
    # 기본 정보
    suspect_id: int = Field(description="용의자 고유 ID (1, 2, 3...)")
    name: str = Field(description="이름")
    role: str = Field(description="역할/직업")
    age: int = Field(description="나이")
    gender: str = Field(description="성별")
    description: str = Field(description="외모/특징 설명")

    # 게임 핵심 정보
    is_culprit: bool = Field(description="범인 여부")
    motive: Optional[str] = Field(default=None, description="범인인 경우 동기")
    alibi_summary: str = Field(description="알리바이 요약 (한 문장)")

    # 타임라인
    timeline: List[TimelineEntrySchema] = Field(description="시간대별 행적")

    # 단계별 비밀 (Pressure 기반)
    secrets: List[SecretTierSchema] = Field(
        description="pressure threshold 순으로 정렬된 비밀 목록 (최소 5개: 0, 30, 50, 70, 90)"
    )

    # 성격
    personality: PersonalitySchema = Field(description="성격 및 말투")

    # 핵심 증거 (자백 트리거)
    critical_evidence_ids: List[int] = Field(
        default=[],
        description="모두 제시 시 자백 유도 가능한 핵심 증거 ID들"
    )


class SuspectListSchema(BaseModel):
    """용의자 목록"""
    suspects: List[SuspectSchema]
