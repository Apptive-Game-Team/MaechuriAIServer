"""Repository for Asset database operations."""
from contextlib import asynccontextmanager
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory
from app.db.models.asset import Asset


class AssetRepository:
    """Data access layer for Asset entities.

    Supports basic CRUD operations and embedding-based semantic search
    using pgvector cosine distance.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self._external_session = session

    @asynccontextmanager
    async def _get_session(self):
        """Get session - use external if provided, else create new."""
        if self._external_session:
            yield self._external_session
        else:
            async with async_session_factory() as session:
                yield session

    async def get_by_id(self, asset_id: int) -> Optional[Asset]:
        """Retrieve a single asset by its primary key.

        Parameters
        ----------
        asset_id : int
            The asset primary key.

        Returns
        -------
        Asset or None
        """
        async with self._get_session() as session:
            stmt = select(Asset).where(Asset.id == asset_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all(self) -> List[Asset]:
        """Retrieve all assets.

        Returns
        -------
        List[Asset]
        """
        async with self._get_session() as session:
            stmt = select(Asset)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def save(self, asset: Asset) -> Asset:
        """Persist a new or updated Asset.

        Parameters
        ----------
        asset : Asset
            The ORM instance to save.

        Returns
        -------
        Asset
            The saved (and refreshed) instance.
        """
        async with self._get_session() as session:
            session.add(asset)
            await session.commit()
            await session.refresh(asset)
            return asset

    async def search_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        status: Optional[str] = None,
    ) -> List[Asset]:
        """Search assets by semantic similarity to a query embedding.

        Uses pgvector cosine distance (<=> operator) to rank results.

        Parameters
        ----------
        query_embedding : List[float]
            The 1024-dimensional query vector produced by BGE-M3.
        top_k : int, optional
            Number of top results to return. Defaults to 5.
        status : str, optional
            Filter results to assets with this status (e.g. 'COMPLETED').
            If None, all statuses are returned.

        Returns
        -------
        List[Asset]
            Assets ordered by ascending cosine distance (most similar first).
        """
        async with self._get_session() as session:
            conditions = [Asset.embedding.isnot(None)]
            if status is not None:
                conditions.append(Asset.status == status)

            stmt = (
                select(Asset)
                .where(*conditions)
                .order_by(Asset.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_embedding(self, asset_id: int, embedding: List[float]) -> bool:
        """Store or replace the embedding for an existing asset.

        Parameters
        ----------
        asset_id : int
            The asset primary key.
        embedding : List[float]
            The new 1024-dimensional embedding vector.

        Returns
        -------
        bool
            True if the asset was found and updated, False otherwise.
        """
        async with self._get_session() as session:
            stmt = select(Asset).where(Asset.id == asset_id)
            result = await session.execute(stmt)
            asset = result.scalar_one_or_none()
            if asset is None:
                return False
            asset.embedding = embedding
            await session.commit()
            return True
