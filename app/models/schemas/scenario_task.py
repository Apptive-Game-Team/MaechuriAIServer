from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ScenarioStatus(str, Enum):
    """시나리오 생성 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScenarioTaskInfo:
    """
    시나리오 생성 태스크 정보

    Attributes
    ----------
    key : str
        태스크 고유 키
    theme : str
        시나리오 테마
    status : ScenarioStatus
        현재 상태
    scenario_id : int | None
        생성된 시나리오 ID (완료 시)
    error : str | None
        에러 메시지 (실패 시)
    """
    def __init__(self, key: str, theme: str):
        self.key = key
        self.theme = theme
        self.status = ScenarioStatus.PENDING
        self.scenario_id: Optional[int] = None
        self.error: Optional[str] = None


class ScenarioCreateRequest(BaseModel):
    """
    시나리오 생성 요청

    Attributes
    ----------
    key : str
        시나리오 생성 태스크 추적용 고유 키
    theme : str
        시나리오 테마 (기본값: "random")
    """
    key: str = Field(..., description="태스크 추적용 고유 키", min_length=1)
    theme: str = Field(default="random", description="시나리오 테마")


class ScenarioStatusResponse(BaseModel):
    """
    시나리오 태스크 상태 응답

    Attributes
    ----------
    key : str
        태스크 키
    status : ScenarioStatus
        현재 상태
    theme : str
        시나리오 테마
    scenario_id : int | None
        생성된 시나리오 ID (완료 시)
    error : str | None
        에러 메시지 (실패 시)
    """
    key: str
    status: ScenarioStatus
    theme: str
    scenario_id: Optional[int] = None
    error: Optional[str] = None


class ScenarioCreateResponse(BaseModel):
    """
    시나리오 생성 시작 응답

    Attributes
    ----------
    key : str
        태스크 키
    message : str
        응답 메시지
    status : ScenarioStatus
        초기 상태
    theme : str
        시나리오 테마
    scenario_id : int | None
        이미 존재하는 경우 시나리오 ID
    """
    key: str
    message: str
    status: ScenarioStatus
    theme: str
    scenario_id: Optional[int] = None


class ScenarioTaskListResponse(BaseModel):
    """
    시나리오 태스크 목록 응답

    Attributes
    ----------
    total : int
        전체 태스크 개수
    tasks : list[dict]
        태스크 정보 목록
    """
    total: int
    tasks: list[dict]
