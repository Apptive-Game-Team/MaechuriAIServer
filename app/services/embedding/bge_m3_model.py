"""BGE-M3 embedding model for RAG."""
from typing import List
from sentence_transformers import SentenceTransformer

from app.services.embedding.embedding_model import EmbeddingModel


# BGE-M3 model from Hugging Face
MODEL_NAME = "BAAI/bge-m3"


class BGEM3Model(EmbeddingModel):
    """Embedding model based on BGE-M3 from BAAI.

    BGE-M3 is a multilingual embedding model that supports:
    - 100+ languages including Korean
    - 1024 dimensions
    - 8192 max tokens
    - Dense, sparse, and multi-vector retrieval

    This implementation uses dense embeddings only via SentenceTransformer.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name_or_path: str = MODEL_NAME, device: str = 'cpu') -> None:
        """Initialize the BGE-M3 model.
        TODO : device 설정 필요

        Parameters
        ----------
        model_name_or_path : str, optional
            The HuggingFace model name or local path. Defaults to BAAI/bge-m3.
        device : str, optional
            Device to run model on ('cuda', 'cpu', etc.). Auto-detected if None.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.model = SentenceTransformer(
          model_name_or_path,
          device=device,
          model_kwargs={"low_cpu_mem_usage": False}
        )
        self._initialized = True

    @property
    def dimension(self) -> int:
        """Return embedding dimension (1024 for BGE-M3)."""
        return 1024

    def embed(self, text: str) -> List[float]:
        """Compute an embedding vector for the given text.

        Parameters
        ----------
        text : str
            The input text to encode as an embedding.

        Returns
        -------
        List[float]
            The embedding of the input text as a list of 1024 floating-point values.
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Compute embeddings for multiple texts efficiently.

        Parameters
        ----------
        texts : List[str]
            The input texts to encode.
        batch_size : int, optional
            Batch size for encoding. Defaults to 32.

        Returns
        -------
        List[List[float]]
            List of embedding vectors.
        """
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a query with instruction prefix for better retrieval.

        BGE models recommend adding instruction prefix for queries.

        Parameters
        ----------
        query : str
            The query text to encode.

        Returns
        -------
        List[float]
            The query embedding.
        """
        # BGE-M3 recommends no instruction prefix, but we keep method for API consistency
        return self.embed(query)

    def embed_documents(self, documents: List[str], batch_size: int = 32) -> List[List[float]]:
        """Embed multiple documents for storage/indexing.

        Parameters
        ----------
        documents : List[str]
            The documents to encode.
        batch_size : int, optional
            Batch size for encoding. Defaults to 32.

        Returns
        -------
        List[List[float]]
            List of document embeddings.
        """
        return self.embed_batch(documents, batch_size=batch_size)


# Singleton instance getter
_model_instance: BGEM3Model = None


def get_embedding_model() -> BGEM3Model:
    """Get the singleton BGE-M3 model instance.

    Returns
    -------
    BGEM3Model
        The BGE-M3 embedding model instance.
    """
    global _model_instance
    if _model_instance is None:
        _model_instance = BGEM3Model()
    return _model_instance


if __name__ == "__main__":
    """Test the BGE-M3 model."""
    import torch
    from sentence_transformers import util

    print("Loading BGE-M3 model...")
    model = get_embedding_model()
    print(f"Model loaded! Dimension: {model.dimension}")

    # Test Korean sentences
    sentences = [
        "어젯밤 10시에 뭐 했어?",
        "10시쯤 도서관에서 책을 읽고 있었습니다.",
        "범행 현장에서 발견된 칼에 대해 설명해주세요.",
        "오늘 날씨가 좋네요.",
    ]

    print("\nComputing embeddings...")
    embeddings = model.embed_batch(sentences)
    embeddings_tensor = torch.tensor(embeddings)

    print("\nSimilarity matrix:")
    for i, s1 in enumerate(sentences):
        for j, s2 in enumerate(sentences):
            if i < j:
                sim = util.cos_sim(embeddings_tensor[i], embeddings_tensor[j]).item()
                print(f"  [{i}] vs [{j}]: {sim:.4f}")
                print(f"    - {s1[:30]}...")
                print(f"    - {s2[:30]}...")
