"""Asset search service using BGE-M3 embeddings."""
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
            each containing a cosine similarity score (typically -1.0 to 1.0).
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
                raise RuntimeError(
                    f"Failed to update embedding for asset {asset.id} "
                    f"(prompt length={len(asset.prompt or '')})."
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
