from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated

from app.services.scenario.scenario_service import ScenarioService
from app.api.dependencies.scenario_dependencies import get_scenario_service
from app.models.schemas.solve import ScenarioSolveRequest, ScenarioSolveResponse

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

@router.post("/daily")
async def create_daily_scenario(
        theme: str = "random",
        scenario_service: ScenarioService = Annotated[ScenarioService, Depends(get_scenario_service)]):
    """
    Creates a new daily mystery scenario.
    """
    try:
        # ScenarioService를 호출하여 시나리오 생성 (Case -> Skeleton -> Expansion -> Clues)
        result = scenario_service.generate(theme)
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
