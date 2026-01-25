from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class SolveResultStatus(str, Enum):
    """추리 결과 상태"""
    CORRECT = "correct"      # 범인 맞음 + 추리 70점 이상
    PARTIAL = "partial"      # 범인 맞음 + 추리 70점 미만
    INCORRECT = "incorrect"  # 범인 틀림


class CulpritMatchResult(BaseModel):
    """범인 매칭 결과"""
    expected: List[int] = Field(description="정답 범인 ID 목록")
    submitted: List[int] = Field(description="제출된 범인 ID 목록")
    is_match: bool = Field(description="범인 일치 여부")
    match_rate: float = Field(ge=0.0, le=1.0, description="일치율 (0.0 ~ 1.0)")


class ScenarioSolveRequest(BaseModel):
    """시나리오 해결 요청"""
    scenario_id: int
    culprit_id: List[int] = Field(min_length=1, description="제출할 범인 ID 목록")
    user_solution: str = Field(
        min_length=10,
        max_length=2000,
        description="유저의 추리 내용"
    )


class ScenarioSolveResponse(BaseModel):
    """시나리오 해결 응답"""
    scenario_id: int
    status: SolveResultStatus = Field(description="결과 상태")
    success: bool = Field(description="성공 여부 (CORRECT일 때 True)")

    # 점수 체계
    culprit_score: float = Field(
        ge=0.0, le=100.0,
        description="범인 점수 (맞으면 100, 틀리면 0)"
    )
    reasoning_score: float = Field(
        ge=0.0, le=100.0,
        description="추리 점수 (0~100)"
    )
    total_score: float = Field(
        ge=0.0, le=100.0,
        description="총점 (범인 40% + 추리 60%)"
    )

    # 상세 결과
    culprit_match: CulpritMatchResult = Field(description="범인 매칭 상세 결과")
    similarity_score: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="임베딩 유사도 점수"
    )

    # 피드백
    message: str = Field(description="결과 메시지")
    feedback: Optional[str] = Field(default=None, description="상세 피드백")
    hints: Optional[List[str]] = Field(default=None, description="힌트 목록 (오답 시)")


class SolveValidationResult(BaseModel):
    """LLM 검증 결과 (내부용)"""
    culprit_score: int = Field(
        ge=0, le=20,
        description="범인 언급 정확도 (0~20)"
    )
    motive_score: int = Field(
        ge=0, le=20,
        description="동기 파악 정확도 (0~20)"
    )
    method_score: int = Field(
        ge=0, le=20,
        description="수법 파악 정확도 (0~20)"
    )
    time_score: int = Field(
        ge=0, le=20,
        description="시간 파악 정확도 (0~20)"
    )
    location_score: int = Field(
        ge=0, le=20,
        description="장소 파악 정확도 (0~20)"
    )
    total_score: int = Field(
        ge=0, le=100,
        description="총점 (0~100)"
    )
    feedback: str = Field(description="피드백 (한국어)")
    missing_elements: List[str] = Field(
        default_factory=list,
        description="놓친 핵심 요소들"
    )
