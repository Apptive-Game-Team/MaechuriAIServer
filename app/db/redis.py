"""
Async Redis connection
"""
import redis.asyncio as redis
from app.core.config import settings


def get_redis_client() -> redis.Redis:
    """
    Redis 클라이언트를 생성합니다.

    Returns
    -------
    redis.Redis
        비동기 Redis 클라이언트
    """
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True
    )


# 싱글톤 Redis 클라이언트
redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """
    Redis 클라이언트 의존성

    Returns
    -------
    redis.Redis
        비동기 Redis 클라이언트
    """
    global redis_client
    if redis_client is None:
        redis_client = get_redis_client()
    return redis_client


async def close_redis():
    """Redis 연결 종료"""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
