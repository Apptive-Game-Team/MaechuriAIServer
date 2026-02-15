from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from app.api.routes.scenario import router as scenario_router
from app.api.routes.chat import router as chat_router
from app.db.redis import close_redis
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start up
    logger.info("Loading BGE-M3 embedding model...")
    from app.services.embedding import get_embedding_model
    get_embedding_model()
    logger.info("BGE-M3 embedding model loaded.")
    yield
    # Shutdown
    await close_redis()


def create_app() -> FastAPI:
    """
    Factory function for creating FastAPI app
    :return: FastAPI app
    """
    app = FastAPI(
        title="MaechuriAIServer",
        description="MaechuriAIServer",
        version="0.0.1",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(scenario_router)
    app.include_router(chat_router)

    # 모델 로드 등 초기화 로직 필요
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)