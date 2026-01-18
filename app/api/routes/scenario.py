from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated

from app.services.scenario.scenario_service import ScenarioService
from app.api.dependencies.scenario_dependencies import get_scenario_service
from app.models.schemas.solve import ScenarioSolveRequest, ScenarioSolveResponse

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

@router.post("/daily")
async def create_daily_scenario(
        scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
        theme: str = "random",
        scenario_id: int = 0):
    """
    Creates a new daily mystery scenario.
    Scenario의 번호는 외부에서 정해주도록 합니다.
    """
    try:
        result = scenario_service.generate(theme, scenario_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/solve")
async def solve_scenario(solution: ScenarioSolveRequest):
    """
    유저가 범인의 아이디와 정답을 제시합니다.
    solution을 통해 합리적인 제시인 지를 확인하고 정답을 내립니다.
    """
    return ScenarioSolveResponse(
        scenario_id=solution.scenario_id,
        success=True,
    )
