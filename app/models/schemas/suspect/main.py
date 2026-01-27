from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.schemas.suspect import PersonalitySchema, SuspectGenerationSchema
from app.models.schemas.suspect.common import FactSchema


class SuspectSchema(BaseModel):
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

    facts: List[FactSchema] = Field(description="")

    # Personality
    personality: "PersonalitySchema" = Field(description="성격 및 말투")

    # Critical clues for confession
    critical_clue_ids: List[int] = Field(
        default=[],
        description="모두 제시 시 자백 유도 가능한 핵심 단서 ID들"
    )

    @classmethod
    def from_generation(cls, generation: "SuspectGenerationSchema") -> "SuspectSchema":
        timeline = [FactSchema.from_timeline(t) for t in generation.timeline]
        secrets = [FactSchema.from_secret(s) for s in generation.secrets]
        return cls(
            suspect_id=generation.suspect_id,
            name=generation.name,
            role=generation.role,
            age=generation.age,
            gender=generation.gender,
            description=generation.description,
            is_culprit=generation.is_culprit,
            motive=generation.motive,
            alibi_summary=generation.alibi_summary,
            facts=timeline.extend(secrets),
            personality=generation.personality,
            critical_clue_ids=generation.critical_clue_ids,
        )


class SuspectListSchema(BaseModel):
    """List of suspects."""
    suspects: List[SuspectSchema]