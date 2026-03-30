"""Asset search service using BGE-M3 embeddings."""
import asyncio
import sys
from dataclasses import dataclass
from typing import List, Optional

from app.db.models.asset import Asset
from app.db.repositories.asset_repository import AssetRepository
from app.services.embedding.embedding_service import EmbeddingService, get_embedding_service


@dataclass
class AssetSearchResult:
    """Single asset search result."""
    asset: Asset
    prompt: Optional[str]
    final_url: Optional[str]
    raw_url: Optional[str]
    resized_url: Optional[str]
    status: str
    similarity: float = 0.0


class AssetSearcher:
    """Semantic search over Asset records using BGE-M3 prompt embeddings.

    Embeds an incoming query with the same BGE-M3 model used throughout the
    project, then delegates to :class:`AssetRepository` for pgvector cosine
    distance search.

    Usage::

        searcher = AssetSearcher()
        results = await searcher.search("밝은 햇살이 비치는 정원 배경")
    """

    def __init__(
        self,
        repository: Optional[AssetRepository] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self._repository = repository or AssetRepository()
        self._embedding_service = embedding_service or get_embedding_service()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        status: Optional[str] = None,
    ) -> List[AssetSearchResult]:
        """Search assets whose prompts are semantically similar to *query*.

        Parameters
        ----------
        query : str
            Natural-language search query (Korean or English).
        top_k : int, optional
            Maximum number of results to return. Defaults to 5.
        status : str, optional
            Restrict results to assets with this status value (e.g. ``'COMPLETED'``).
            Pass ``None`` to include all statuses.

        Returns
        -------
        List[AssetSearchResult]
            Search results ordered from most similar to least similar,
            each containing a ``similarity`` score between 0.0 and 1.0.
        """
        query_embedding = self._embedding_service.embed_query(query)
        pairs = await self._repository.search_with_scores(
            query_embedding=query_embedding,
            top_k=top_k,
            status=status,
        )
        return [self._to_result(asset, score) for asset, score in pairs]

    async def index_unindexed(self) -> int:
        """Find all assets with a NULL embedding and generate embeddings for them.

        Only assets that have a non-empty ``prompt`` are processed.

        Returns
        -------
        int
            Number of assets that were successfully indexed.
        """
        assets = await self._repository.get_unindexed()
        count = 0
        for asset in assets:
            if not asset.prompt:
                continue
            await self.index_asset(asset)
            count += 1
        return count

    async def index_asset(self, asset: Asset) -> Asset:
        """Generate and store the embedding for an asset's prompt.

        If the asset has no prompt, the embedding is left unchanged.
        When the asset already exists in the database (has an ``id``), only the
        embedding column is updated via :meth:`AssetRepository.update_embedding`.
        For brand-new assets (no ``id`` yet), call
        :meth:`AssetRepository.save` first, then call this method.

        Parameters
        ----------
        asset : Asset
            The ORM instance to index.

        Returns
        -------
        Asset
            The asset with the ``embedding`` field populated (if a prompt exists).
        """
        if not asset.prompt:
            return asset
        embedding = self._embedding_service.embed_asset_prompt(asset.prompt)
        if asset.id is not None:
            updated = await self._repository.update_embedding(asset.id, embedding)
            if not updated:
                prompt_len = len(asset.prompt or "")
                raise RuntimeError(
                    f"Failed to update embedding for asset {asset.id} "
                    f"(prompt length={prompt_len})."
                )
            asset.embedding = embedding
        else:
            asset.embedding = embedding
            await self._repository.save(asset)
        return asset

    @staticmethod
    def _to_result(asset: Asset, similarity: float = 0.0) -> AssetSearchResult:
        return AssetSearchResult(
            asset=asset,
            prompt=asset.prompt,
            final_url=asset.final_url,
            raw_url=asset.raw_url,
            resized_url=asset.resized_url,
            status=asset.status,
            similarity=similarity,
        )


# ---------------------------------------------------------------------------
# Demo: python -m app.services.asset.asset_searcher
# ---------------------------------------------------------------------------

async def _demo(query: str, top_k: int = 5) -> None:
    """데모 실행: 미인덱싱 Asset 임베딩 후 쿼리 검색."""
    from dotenv import load_dotenv
    load_dotenv()

    searcher = AssetSearcher()

    # 1) embedding이 비어있는 Asset들에 임베딩 생성 및 저장
    print("=" * 60)
    print("1단계: embedding 미생성 Asset 인덱싱")
    print("=" * 60)
    indexed = await searcher.index_unindexed()
    print(f"  → {indexed}개 Asset에 임베딩을 생성했습니다.\n")

    # 2) 쿼리 문자열로 유사 Asset 검색 후 결과 출력
    print("=" * 60)
    print(f"2단계: 검색 쿼리 → \"{query}\"")
    print("=" * 60)
    results = await searcher.search(query, top_k=top_k)

    if not results:
        print("  검색 결과가 없습니다.")
        return

    for rank, r in enumerate(results, start=1):
        stars = _score_to_stars(r.similarity)
        print(f"\n  [{rank}위]  유사도: {stars}  ({r.similarity:.4f})")
        print(f"  prompt  : {r.prompt or '(없음)'}")
        print(f"  raw_url : {r.raw_url or '(없음)'}")


def _score_to_stars(similarity: float, max_stars: int = 5) -> str:
    """코사인 유사도 값(0~1)을 별(★) 표시로 변환합니다."""
    similarity = max(0.0, min(similarity, 1.0))
    filled = min(round(similarity * max_stars), max_stars)
    return "★" * filled + "☆" * (max_stars - filled)


if __name__ == "__main__":
    # 사용법: python -m app.services.asset.asset_searcher "검색할 내용"
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    search_query = sys.argv[1] if len(sys.argv) > 1 else "밝은 햇살이 비치는 정원 배경"
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    asyncio.run(_demo(search_query, top_k=k))
