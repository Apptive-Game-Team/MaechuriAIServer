from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.scenario.scenario_service import ScenarioService
from app.services.rag import get_rag_service, RAGService
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


@router.post("/{scenario_id}/index")
async def index_scenario(
        scenario_id: int,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    시나리오 데이터를 RAG용으로 인덱싱합니다.

    시나리오 생성 후 이 엔드포인트를 호출하여 용의자, 증거 등의 임베딩을 생성합니다.
    이 작업이 완료되어야 RAG 기능이 활성화됩니다.
    """
    try:
        rag_service = get_rag_service()
        stats = await rag_service.index_scenario(db, scenario_id)
        return {
            "scenario_id": scenario_id,
            "indexed": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


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
