"""Global / shared infrastructure package.

This package groups all components that are shared across features — they are
not owned by any single feature domain but are consumed by both the scenario
generation and chat features.

Sub-packages
------------
llm
    Abstract :class:`LLMClient` interface and the concrete
    :class:`GeminiClient` implementation.
embedding
    Sentence-embedding model wrapper (:class:`BGEModel` / :class:`SBERTModel`)
    and the :func:`get_embedding_model` singleton factory.
rag
    Retrieval-Augmented Generation pipeline: :class:`RAGService`,
    :class:`RAGRetriever`, :class:`RAGIndexer`, :class:`ContextBuilder`.
agent
    Shared LLM agents used by scenario generation and chat flows.
db
    SQLAlchemy async session factory, ORM entity models, and repository
    classes (:class:`ScenarioRepository`, :class:`GameSessionRepository`).

Typical import paths
--------------------
>>> from app.features.global_ import GeminiClient, get_embedding_model
>>> from app.features.global_ import get_rag_service
>>> from app.features.global_.db import ScenarioRepository
"""
__all__ = ["LLMClient", "GeminiClient", "get_embedding_model", "get_rag_service"]


def __getattr__(name: str):
    if name == "LLMClient":
        from app.features.global_.llm.llm_client import LLMClient
        return LLMClient
    if name == "GeminiClient":
        from app.features.global_.llm.gemini_client import GeminiClient
        return GeminiClient
    if name == "get_embedding_model":
        from app.features.global_.embedding import get_embedding_model
        return get_embedding_model
    if name == "get_rag_service":
        from app.features.global_.rag import get_rag_service
        return get_rag_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
