from logger import logger
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.scenario.scenario_service import ScenarioService
from app.services.rag import get_rag_service
from app.api.dependencies.scenario_dependencies import get_scenario_service
from app.models.schemas.solve import ScenarioSolveRequest, ScenarioSolveResponse
from app.models.schemas.scenario_task import (
    ScenarioStatus,
    ScenarioTaskInfo,
    ScenarioCreateRequest,
    ScenarioCreateResponse,
    ScenarioStatusResponse,
    ScenarioTaskListResponse
)

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

# 백그라운드 태스크 상태 관리
scenario_tasks: dict[str, ScenarioTaskInfo] = {}


async def create_scenario_background(
        db: AsyncSession,
        scenario_service: ScenarioService,
        key: str,
        theme: str = "random",
):
    """
    백그라운드에서 시나리오를 생성하고 DB에 저장합니다.

    Parameters
    ----------
    db : AsyncSession
        데이터베이스 세션
    scenario_service : ScenarioService
        시나리오 서비스
    key : str
        태스크 추적용 고유 키
    theme : str
        시나리오 테마
    """
    logger.info(f"[{key}] Starting background scenario generation with theme: {theme}")

    if key not in scenario_tasks:
        logger.error(f"[{key}] Task not found in scenario_tasks")
        return

    task_info = scenario_tasks[key]
    task_info.status = ScenarioStatus.PROCESSING

    try:
        # 시나리오 생성 및 저장
        scenario_data, scenario_id = await scenario_service.generate_and_save(
            pre_input=theme,
            db=db
        )

        task_info.scenario_id = scenario_id
        task_info.status = ScenarioStatus.COMPLETED

        logger.info(f"[{key}] ✅ Scenario generated successfully. ID: {scenario_id}")

    except Exception as e:
        task_info.status = ScenarioStatus.FAILED
        task_info.error = str(e)
        logger.error(f"[{key}] ❌ Scenario generation failed: {e}", exc_info=True)

@router.post("/daily", response_model=ScenarioCreateResponse)
async def create_daily_scenario(
        request: ScenarioCreateRequest,
        background_tasks: BackgroundTasks,
        scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
        db: Annotated[AsyncSession, Depends(get_db)]):
    """
    새로운 데일리 미스터리 시나리오를 생성합니다 (백그라운드).

    Parameters
    ----------
    request : ScenarioCreateRequest
        시나리오 생성 요청 (key, theme)

    Returns
    -------
    ScenarioCreateResponse
        생성 시작 메시지, 상태, key, theme

    Notes
    -----
    - 시나리오 생성은 백그라운드에서 진행됩니다
    - GET /api/scenarios/status?key={key}로 진행 상태 확인
    - GET /api/scenarios/id?key={key}로 완료된 시나리오 ID 조회
    """
    key = request.key
    theme = request.theme

    # 이미 진행 중인 태스크 체크
    if key in scenario_tasks:
        existing_task = scenario_tasks[key]
        if existing_task.status == ScenarioStatus.PROCESSING:
            raise HTTPException(
                status_code=409,
                detail=f"Scenario generation already in progress for key: {key}"
            )
        elif existing_task.status == ScenarioStatus.COMPLETED:
            return ScenarioCreateResponse(
                key=key,
                message="Scenario already exists",
                status=existing_task.status,
                theme=existing_task.theme,
                scenario_id=existing_task.scenario_id
            )

    # 새 태스크 등록
    task_info = ScenarioTaskInfo(key=key, theme=theme)
    scenario_tasks[key] = task_info

    # 백그라운드 태스크 시작
    background_tasks.add_task(create_scenario_background, db, scenario_service, key, theme)

    logger.info(f"[{key}] Scenario generation task queued with theme: {theme}")

    return ScenarioCreateResponse(
        key=key,
        message="Scenario generation started",
        status=ScenarioStatus.PENDING,
        theme=theme
    )


@router.get("/data/{scenario_id}")
async def get_scenario(
        scenario_id: int,
        scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)]
):
    """
    시나리오 ID로 시나리오 데이터를 조회합니다.

    Parameters
    ----------
    scenario_id : int
        조회할 시나리오 ID

    Returns
    -------
    dict
        시나리오 전체 데이터 (사건, 용의자, 단서, 맵 등)
        :param scenario_id:
        :param scenario_service:
    """
    try:
        scenario_data = await scenario_service.repository.get_scenario_by_id(scenario_id)

        if scenario_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Scenario with ID {scenario_id} not found"
            )

        return scenario_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve scenario {scenario_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve scenario: {str(e)}"
        )


@router.post("/data/{scenario_id}/index")
async def index_scenario(
        scenario_id: int,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    시나리오 데이터를 RAG용으로 인덱싱합니다.

    Parameters
    ----------
    scenario_id : int
        인덱싱할 시나리오 ID

    Returns
    -------
    dict
        인덱싱 결과 및 통계

    Notes
    -----
    시나리오 생성 후 이 엔드포인트를 호출하여 용의자, 증거 등의 임베딩을 생성합니다.
    이 작업이 완료되어야 RAG 기능이 활성화됩니다.
    """
    try:
        rag_service = get_rag_service()
        stats = await rag_service.index_scenario(db, scenario_id)

        logger.info(f"[Scenario {scenario_id}] RAG indexing completed: {stats}")

        return {
            "scenario_id": scenario_id,
            "indexed": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"[Scenario {scenario_id}] RAG indexing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Indexing failed: {str(e)}"
        )


@router.post("/solve")
async def solve_scenario(
        solution: ScenarioSolveRequest,
        scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)]
):
    """
    유저가 범인과 추리를 제시하여 시나리오를 해결합니다.

    Parameters
    ----------
    solution : ScenarioSolveRequest
        시나리오 ID, 범인 ID, 추리 내용 등

    Returns
    -------
    ScenarioSolveResponse
        정답 여부 및 피드백

    Notes
    -----
    TODO: 실제 정답 검증 로직 구현 필요
    - 시나리오에서 정답 범인 조회
    - 제시된 추리의 합리성 평가 (LLM 활용)
    - 부분 점수 또는 힌트 제공
    """
    try:
        # TODO: 실제 검증 로직 구현
        # 1. scenario_id로 시나리오 데이터 조회
        # 2. ground_truth와 비교
        # 3. 추리 내용 평가 (LLM)
        # 4. 결과 반환

        logger.info(f"[Scenario {solution.scenario_id}] Solve attempt received")

        # 임시 구현 (항상 성공)
        return ScenarioSolveResponse(
            scenario_id=solution.scenario_id,
            success=True,
            message="Solution evaluated (placeholder implementation)"
        )

    except Exception as e:
        logger.error(f"[Scenario {solution.scenario_id}] Solve evaluation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate solution: {str(e)}"
        )

@router.get("/tasks", response_model=ScenarioTaskListResponse)
async def get_all_tasks():
    """
    모든 시나리오 생성 태스크를 조회합니다.

    Returns
    -------
    ScenarioTaskListResponse
        모든 태스크 목록
    """
    tasks = []
    for task_key, task_info in scenario_tasks.items():
        tasks.append(ScenarioStatusResponse(
            key=task_key,
            status=task_info.status,
            theme=task_info.theme,
            scenario_id=task_info.scenario_id,
            error=task_info.error
        ))

    return ScenarioTaskListResponse(
        total=len(tasks),
        tasks=tasks
    )


@router.get("/tasks/{key}", response_model=ScenarioStatusResponse)
async def get_task_status(key: str):
    """
    태스크 키로 태스크 진행 상태 및 결과를 조회합니다.

    Parameters
    ----------
    key : str
        조회할 태스크 키

    Returns
    -------
    ScenarioStatusResponse
        태스크 상세 상태
    """
    task_info = scenario_tasks.get(key)
    if task_info is None:
        raise HTTPException(
            status_code=404,
            detail=f"No task found for key: {key}"
        )

    return ScenarioStatusResponse(
        key=key,
        status=task_info.status,
        theme=task_info.theme,
        scenario_id=task_info.scenario_id,
        error=task_info.error
    )
