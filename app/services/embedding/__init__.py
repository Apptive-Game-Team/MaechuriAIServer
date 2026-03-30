__all__ = [
    "EmbeddingModel",
    "BGEM3Model",
    "get_embedding_model",
    "EmbeddingService",
    "get_embedding_service",
]


def __getattr__(name: str):
    if name == "EmbeddingModel":
        from app.features.global_.embedding.embedding_model import EmbeddingModel
        return EmbeddingModel
    if name in {"BGEM3Model", "get_embedding_model"}:
        from app.features.global_.embedding.bge_m3_model import BGEM3Model, get_embedding_model
        return BGEM3Model if name == "BGEM3Model" else get_embedding_model
    if name in {"EmbeddingService", "get_embedding_service"}:
        from app.features.global_.embedding.embedding_service import EmbeddingService, get_embedding_service
        return EmbeddingService if name == "EmbeddingService" else get_embedding_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
