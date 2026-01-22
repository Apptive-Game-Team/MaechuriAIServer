import sys
import asyncio
import pytest

# Windows 환경에서 ProactorEventLoop 대신 SelectorEventLoop 사용
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture(autouse=True)
async def reset_db_engine():
    """
    Ensure the DB engine is clean before each test.
    This prevents 'attached to a different loop' errors when pytest-asyncio
    creates a new loop for each test function.
    """
    from app.db.database import engine
    await engine.dispose()

