from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.suspect import SuspectSchema
from app.services.scenario.fact_generation_graph import (
    FactGenerationGraph,
    ResolvedFact,
)

if TYPE_CHECKING:
    from app.db.repositories.scenario_repository import ScenarioRepository
    from app.services.llm.llm_client import LLMClient
    from app.services.rag import RAGService


class SuspectSelfInfoTool:
    """Tool suspects use to resolve self-related uncertainty."""

    def __init__(
        self,
        *,
        scenario_repository: "ScenarioRepository",
        rag_service: "RAGService",
        llm_client: "LLMClient",
    ):
        self.fact_graph = FactGenerationGraph(
            scenario_repository=scenario_repository,
            rag_service=rag_service,
            llm_client=llm_client,
        )

    async def aresolve(
        self,
        *,
        db: AsyncSession,
        scenario_id: int,
        suspect_id: int,
        suspect: SuspectSchema,
        wonder: str,
    ) -> ResolvedFact:
        return await self.fact_graph.aresolve(
            db=db,
            scenario_id=scenario_id,
            suspect_id=suspect_id,
            suspect=suspect,
            wonder=wonder,
        )
