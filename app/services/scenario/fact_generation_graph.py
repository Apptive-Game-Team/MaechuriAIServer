from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Fact
from app.models.schemas.suspect import SuspectSchema
from app.services.agent.fact_generator import FactGenerator
from app.services.llm.llm_client import LLMClient

if TYPE_CHECKING:
    from app.db.repositories.scenario_repository import ScenarioRepository
    from app.services.rag import RAGService


@dataclass
class ResolvedFact:
    """Result returned by the suspect self-info fact tool."""

    fact_id: int
    text: str
    source: str
    created: bool


class FactGenerationState(TypedDict, total=False):
    db: AsyncSession
    scenario_id: int
    suspect_id: int
    suspect: SuspectSchema
    wonder: str
    scenario: dict
    existing_fact: Any
    generated_text: str
    generated_reasoning: str
    resolved_fact: ResolvedFact


class FactGenerationGraph:
    """Graph for resolving or creating canonical facts during gameplay.

    The graph always loads the full scenario before it generates a fact, then
    updates RAG through RAGService instead of indexing in a separate workflow.
    """

    def __init__(
        self,
        *,
        scenario_repository: "ScenarioRepository",
        rag_service: "RAGService",
        llm_client: LLMClient,
    ):
        self.scenario_repository = scenario_repository
        self.rag_service = rag_service
        self.fact_generator = FactGenerator(llm_client)
        self.graph = self._build_graph()

    async def aresolve(
        self,
        *,
        db: AsyncSession,
        scenario_id: int,
        suspect_id: int,
        suspect: SuspectSchema,
        wonder: str,
    ) -> ResolvedFact:
        state = await self.graph.ainvoke(
            {
                "db": db,
                "scenario_id": scenario_id,
                "suspect_id": suspect_id,
                "suspect": suspect,
                "wonder": wonder,
            }
        )
        resolved = state.get("resolved_fact")
        if resolved is None:
            raise RuntimeError("Fact generation graph finished without a result")
        return resolved

    def _build_graph(self):
        builder = StateGraph(FactGenerationState)
        builder.add_node("load_scenario", self._load_scenario)
        builder.add_node("find_existing_fact", self._find_existing_fact)
        builder.add_node("generate_global_fact", self._generate_global_fact)
        builder.add_node("persist_global_fact", self._persist_global_fact)
        builder.add_node("return_existing_fact", self._return_existing_fact)

        builder.add_edge(START, "load_scenario")
        builder.add_edge("load_scenario", "find_existing_fact")
        builder.add_conditional_edges(
            "find_existing_fact",
            self._route_after_search,
            {
                "existing": "return_existing_fact",
                "missing": "generate_global_fact",
            },
        )
        builder.add_edge("return_existing_fact", END)
        builder.add_edge("generate_global_fact", "persist_global_fact")
        builder.add_edge("persist_global_fact", END)

        return builder.compile()

    async def _load_scenario(
        self,
        state: FactGenerationState,
    ) -> FactGenerationState:
        scenario = await self.scenario_repository.get_scenario_by_id(
            state["scenario_id"]
        )
        if scenario is None:
            raise ValueError(f"Scenario {state['scenario_id']} not found")
        return {"scenario": scenario}

    async def _find_existing_fact(
        self,
        state: FactGenerationState,
    ) -> FactGenerationState:
        matches = await self.rag_service.find_self_info_facts(
            db=state["db"],
            scenario_id=state["scenario_id"],
            suspect_id=state["suspect_id"],
            query=state["wonder"],
        )
        return {"existing_fact": matches[0] if matches else None}

    @staticmethod
    def _route_after_search(state: FactGenerationState) -> str:
        return "existing" if state.get("existing_fact") else "missing"

    async def _return_existing_fact(
        self,
        state: FactGenerationState,
    ) -> FactGenerationState:
        fact = state["existing_fact"]
        text = self._fact_text(fact)
        return {
            "resolved_fact": ResolvedFact(
                fact_id=fact.fact_id,
                text=text,
                source=fact.type,
                created=False,
            )
        }

    async def _generate_global_fact(
        self,
        state: FactGenerationState,
    ) -> FactGenerationState:
        generated = await self.fact_generator.agenerate_global_fact(
            scenario=state["scenario"],
            suspect=state["suspect"].model_dump(mode="json"),
            wonder=state["wonder"],
        )
        return {
            "generated_text": generated.text,
            "generated_reasoning": generated.reasoning,
        }

    async def _persist_global_fact(
        self,
        state: FactGenerationState,
    ) -> FactGenerationState:
        db = state["db"]
        fact = None
        for _ in range(3):
            try:
                async with db.begin_nested():
                    next_fact_id = await self._next_fact_id(db, state["scenario_id"])
                    fact = Fact(
                        scenario_id=state["scenario_id"],
                        fact_id=next_fact_id,
                        suspect_id=0,
                        threshold=0,
                        type="global",
                        content={
                            "text": state["generated_text"],
                            "source": "suspect_self_info_tool",
                            "wonder": state["wonder"],
                            "suspect_id": state["suspect_id"],
                            "reasoning": state.get("generated_reasoning", ""),
                        },
                    )
                    db.add(fact)
                    await db.flush()
                break
            except IntegrityError:
                fact = None
        if fact is None:
            raise RuntimeError("Failed to allocate a unique fact_id after retries")
        await self.rag_service.index_fact(db, fact)
        await db.commit()
        return {
            "resolved_fact": ResolvedFact(
                fact_id=fact.fact_id,
                text=state["generated_text"],
                source="global",
                created=True,
            )
        }

    @staticmethod
    async def _next_fact_id(db: AsyncSession, scenario_id: int) -> int:
        result = await db.execute(
            select(func.max(Fact.fact_id)).where(Fact.scenario_id == scenario_id)
        )
        return (result.scalar_one_or_none() or 0) + 1

    @staticmethod
    def _fact_text(fact: Any) -> str:
        content = getattr(fact, "content", "")
        if isinstance(content, dict):
            return (
                content.get("text")
                or content.get("content")
                or str(content)
            )
        return str(content)
