"""
Redis 기반 시나리오 태스크 저장소
"""
import json
from typing import Optional

import redis.asyncio as redis

from app.models.schemas.scenario_task import ScenarioStatus, ScenarioTaskInfo


class ScenarioTaskStore:
    """
    Redis를 사용한 시나리오 태스크 저장소

    Attributes
    ----------
    redis : redis.Redis
        Redis 클라이언트
    prefix : str
        Redis 키 prefix
    ttl : int
        태스크 데이터 TTL (초)
    """

    def __init__(self, redis_client: redis.Redis, prefix: str = "scenario_task:", ttl: int = 86400):
        """
        Parameters
        ----------
        redis_client : redis.Redis
            Redis 클라이언트
        prefix : str
            Redis 키 prefix (기본값: "scenario_task:")
        ttl : int
            태스크 데이터 TTL, 기본값 24시간 (86400초)
        """
        self.redis = redis_client
        self.prefix = prefix
        self.ttl = ttl

    def _key(self, key: str) -> str:
        """Redis 키 생성"""
        return f"{self.prefix}{key}"

    def _serialize(self, task_info: ScenarioTaskInfo) -> str:
        """ScenarioTaskInfo를 JSON 문자열로 직렬화"""
        return json.dumps({
            "key": task_info.key,
            "theme": task_info.theme,
            "status": task_info.status.value,
            "scenario_id": task_info.scenario_id,
            "error": task_info.error
        })

    def _deserialize(self, data: str) -> ScenarioTaskInfo:
        """JSON 문자열을 ScenarioTaskInfo로 역직렬화"""
        obj = json.loads(data)
        task_info = ScenarioTaskInfo(key=obj["key"], theme=obj["theme"])
        task_info.status = ScenarioStatus(obj["status"])
        task_info.scenario_id = obj.get("scenario_id")
        task_info.error = obj.get("error")
        return task_info

    async def get(self, key: str) -> Optional[ScenarioTaskInfo]:
        """
        태스크 정보 조회

        Parameters
        ----------
        key : str
            태스크 키

        Returns
        -------
        ScenarioTaskInfo | None
            태스크 정보, 없으면 None
        """
        data = await self.redis.get(self._key(key))
        if data is None:
            return None
        return self._deserialize(data)

    async def set(self, task_info: ScenarioTaskInfo) -> None:
        """
        태스크 정보 저장

        Parameters
        ----------
        task_info : ScenarioTaskInfo
            저장할 태스크 정보
        """
        await self.redis.set(
            self._key(task_info.key),
            self._serialize(task_info),
            ex=self.ttl
        )

    async def exists(self, key: str) -> bool:
        """
        태스크 존재 여부 확인

        Parameters
        ----------
        key : str
            태스크 키

        Returns
        -------
        bool
            존재하면 True
        """
        return await self.redis.exists(self._key(key)) > 0

    async def delete(self, key: str) -> bool:
        """
        태스크 삭제

        Parameters
        ----------
        key : str
            태스크 키

        Returns
        -------
        bool
            삭제 성공 여부
        """
        return await self.redis.delete(self._key(key)) > 0

    async def get_all(self) -> list[ScenarioTaskInfo]:
        """
        모든 태스크 조회

        Returns
        -------
        list[ScenarioTaskInfo]
            전체 태스크 목록
        """
        keys = await self.redis.keys(f"{self.prefix}*")
        tasks = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                tasks.append(self._deserialize(data))
        return tasks

    async def update_status(
        self,
        key: str,
        status: ScenarioStatus,
        scenario_id: Optional[int] = None,
        error: Optional[str] = None
    ) -> Optional[ScenarioTaskInfo]:
        """
        태스크 상태 업데이트

        Parameters
        ----------
        key : str
            태스크 키
        status : ScenarioStatus
            새로운 상태
        scenario_id : int | None
            시나리오 ID (완료 시)
        error : str | None
            에러 메시지 (실패 시)

        Returns
        -------
        ScenarioTaskInfo | None
            업데이트된 태스크 정보, 없으면 None
        """
        task_info = await self.get(key)
        if task_info is None:
            return None

        task_info.status = status
        if scenario_id is not None:
            task_info.scenario_id = scenario_id
        if error is not None:
            task_info.error = error

        await self.set(task_info)
        return task_info
