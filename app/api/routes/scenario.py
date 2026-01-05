from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from pydantic import BaseModel

from app.services.scenario.scenario_service import ScenarioService

class ScenarioSolve(BaseModel):
    scenario_id: int
    culprit_id: list[int]
    user_id: int
    user_solution: str

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

# ================= Dependency =================
def get_scenario_service() -> ScenarioService:
    return ScenarioService()
# ================= End =================

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
async def solve_scenario(solution: ScenarioSolve):
    """
    유저가 범인의 아이디와 정답을 제시합니다.
    solution을 통해 합리적인 제시인 지를 확인하고 정답을 내립니다.
    """
    return {"message": "Solution submitted (Under construction)",
            "scenario_id": solution.scenario_id,
            "success": True}
