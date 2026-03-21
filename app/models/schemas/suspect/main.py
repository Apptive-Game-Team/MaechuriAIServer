from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.schemas.suspect import PersonalitySchema, SuspectGenerationSchema
from app.models.schemas.suspect.common import FactSchema, HeardContentSchema


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

    # Image generation
    visual_description: Optional[str] = Field(default=None, description="이미지 생성을 위한 생김새 프롬프트 (영어)")

    @classmethod
    def from_generation(cls, generation: "SuspectGenerationSchema") -> "SuspectSchema":
        timeline: List[FactSchema] = [FactSchema.from_timeline(t) for t in generation.timeline]
        # Pass knowledge_type through for each secret (secret vs hidden)
        secrets: List[FactSchema] = [
            FactSchema.from_secret(s, knowledge_type=s.knowledge_type)
            for s in generation.secrets
        ]
        # Convert heard facts (second-hand cross-suspect knowledge)
        heard: List[FactSchema] = [FactSchema.from_heard(h) for h in generation.heard]
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
            facts=timeline + secrets + heard,
            personality=generation.personality,
            visual_description=generation.visual_description,
        )


class SuspectListSchema(BaseModel):
    """List of suspects."""
    suspects: List[SuspectSchema]

from app.models.schemas.suspect.common import PersonalitySchema
from app.models.schemas.suspect.response import SuspectGenerationSchema
SuspectSchema.model_rebuild()