from pydantic import BaseModel
from typing import Optional


class ScenarioSolveRequest(BaseModel):
    """시나리오 해결 요청"""
    scenario_id: int
    culprit_id: list[int]
    user_solution: str


class ScenarioSolveResponse(BaseModel):
    """시나리오 해결 응답"""
    scenario_id: int
    success: bool
    message: Optional[str] = None
    feedback: Optional[str] = None
    score: Optional[float] = None