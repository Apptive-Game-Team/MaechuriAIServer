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
db
    SQLAlchemy async session factory, ORM entity models, and repository
    classes (:class:`ScenarioRepository`, :class:`GameSessionRepository`).

Typical import paths
--------------------
>>> from app.features.global_ import GeminiClient, get_embedding_model
>>> from app.features.global_ import get_rag_service
>>> from app.features.global_.db import ScenarioRepository
"""
# LLM
from app.services.llm.llm_client import LLMClient
from app.services.llm.gemini_client import GeminiClient

# Embedding
from app.services.embedding import get_embedding_model

# RAG
from app.services.rag import get_rag_service

__all__ = [
    # LLM
    "LLMClient",
    "GeminiClient",
    # Embedding
    "get_embedding_model",
    # RAG
    "get_rag_service",
]
