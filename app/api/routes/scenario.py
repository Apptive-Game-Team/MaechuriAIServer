from logger import logger
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, async_session_factory
from app.db.redis import get_redis
from app.services.scenario.scenario_service import ScenarioService
from app.services.scenario.solve_service import SolveService
from app.services.rag import get_rag_service
from app.api.dependencies.scenario_dependencies import get_scenario_service, get_solve_service
from app.services.task import ScenarioTaskStore
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


async def create_scenario_background(
        scenario_service: ScenarioService,
        task_store: ScenarioTaskStore,
        key: str,
        theme: str = "random",
):
    """
    백그라운드에서 시나리오를 생성하고 DB에 저장합니다.

    Parameters
    ----------
    scenario_service : ScenarioService
        시나리오 서비스
    task_store : ScenarioTaskStore
        Redis 태스크 저장소
    key : str
        태스크 추적용 고유 키
    theme : str
        시나리오 테마
    """
    logger.info(f"[{key}] Starting background scenario generation with theme: {theme}")

    task_info = await task_store.get(key)
    if task_info is None:
        logger.error(f"[{key}] Task not found in task_store")
        return

    await task_store.update_status(key, ScenarioStatus.PROCESSING)

    try:
        # 독립적인 DB 세션 생성
        async with async_session_factory() as db:
            # 시나리오 생성 및 저장
            scenario_data, scenario_id = await scenario_service.generate_and_save(
                pre_input=theme,
                db=db
            )

            await task_store.update_status(
                key,
                ScenarioStatus.COMPLETED,
                scenario_id=scenario_id
            )

            logger.info(f"[{key}] Scenario generated successfully. ID: {scenario_id}")

    except Exception as e:
        await task_store.update_status(key, ScenarioStatus.FAILED, error=str(e))
        logger.error(f"[{key}] Scenario generation failed: {e}", exc_info=True)


@router.post("/daily", response_model=ScenarioCreateResponse)
async def create_daily_scenario(
        request: ScenarioCreateRequest,
        background_tasks: BackgroundTasks,
        scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)]
):
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
    - GET /api/scenarios/tasks/{key}로 진행 상태 및 결과를 확인할 수 있습니다

    """
    key = request.key
    theme = request.theme

    # Redis 태스크 저장소 생성
    redis_client = await get_redis()
    task_store = ScenarioTaskStore(redis_client)

    # 이미 진행 중인 태스크 체크
    existing_task = await task_store.get(key)
    if existing_task is not None:
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
    await task_store.set(task_info)

    # 백그라운드 태스크 시작
    background_tasks.add_task(create_scenario_background, scenario_service, task_store, key, theme)

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


@router.post("/solve", response_model=ScenarioSolveResponse)
async def solve_scenario(
        solution: ScenarioSolveRequest,
        solve_service: Annotated[SolveService, Depends(get_solve_service)]
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
    검증 흐름:
    1. 범인 ID 검증 (필수 - 틀리면 바로 오답)
    2. Ground truth 문장 생성 (범인명 + 동기 + 수법 + 시간 + 장소)
    3. 임베딩 유사도 계산 (BGE-M3)
    4. 유사도 >= 0.7 -> 정답
    5. 유사도 < 0.7 -> LLM 추가 검증
    6. 최종 점수 계산 및 응답

    결과 상태:
    - CORRECT: 범인 맞음 + 추리 점수 70점 이상
    - PARTIAL: 범인 맞음 + 추리 점수 70점 미만
    - INCORRECT: 범인 틀림
    """
    try:
        logger.info(f"[Scenario {solution.scenario_id}] Solve attempt received")

        result = await solve_service.solve(
            scenario_id=solution.scenario_id,
            submitted_culprit_ids=solution.culprit_id,
            user_solution=solution.user_solution
        )

        logger.info(
            f"[Scenario {solution.scenario_id}] Solve result: "
            f"status={result.status}, total_score={result.total_score}"
        )

        return result

    except ValueError as e:
        logger.warning(f"[Scenario {solution.scenario_id}] Validation error: {e}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
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
    redis_client = await get_redis()
    task_store = ScenarioTaskStore(redis_client)

    all_tasks = await task_store.get_all()
    tasks = [
        ScenarioStatusResponse(
            key=task_info.key,
            status=task_info.status,
            theme=task_info.theme,
            scenario_id=task_info.scenario_id,
            error=task_info.error
        )
        for task_info in all_tasks
    ]

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
    redis_client = await get_redis()
    task_store = ScenarioTaskStore(redis_client)

    task_info = await task_store.get(key)
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
