__all__ = [
    "RAGIndexer",
    "get_rag_indexer",
    "RAGRetriever",
    "get_rag_retriever",
    "ContextBuilder",
    "get_context_builder",
    "RAGService",
    "get_rag_service",
]


def __getattr__(name: str):
    if name in {"RAGIndexer", "get_rag_indexer"}:
        from app.features.global_.rag.indexer import RAGIndexer, get_rag_indexer
        return RAGIndexer if name == "RAGIndexer" else get_rag_indexer
    if name in {"RAGRetriever", "get_rag_retriever"}:
        from app.features.global_.rag.retriever import RAGRetriever, get_rag_retriever
        return RAGRetriever if name == "RAGRetriever" else get_rag_retriever
    if name in {"ContextBuilder", "get_context_builder"}:
        from app.features.global_.rag.context_builder import ContextBuilder, get_context_builder
        return ContextBuilder if name == "ContextBuilder" else get_context_builder
    if name in {"RAGService", "get_rag_service"}:
        from app.features.global_.rag.rag_service import RAGService, get_rag_service
        return RAGService if name == "RAGService" else get_rag_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
