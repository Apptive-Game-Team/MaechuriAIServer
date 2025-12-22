from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """
    Factory function for creating FastAPI app
    :return: FastAPI app
    """
    app = FastAPI(
        title="MaechuriAIServer",
        description="MaechuriAIServer",
        version="0.0.1",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # app.include_router()

    # 모델 로드 등 초기화 로직 필요
    return app

app = create_app()