import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_DB", "0")

from app.models.schemas.suspect import FactSchema, PersonalitySchema, SuspectSchema
from app.models.schemas.fact_generation import GeneratedGlobalFact
from app.services.scenario.fact_generation_graph import FactGenerationGraph


class FakeScenarioRepository:
    async def get_scenario_by_id(self, scenario_id: int):
        return {
            "scenario_id": scenario_id,
            "incident": {"summary": "연구소에서 벌어진 살인 사건"},
            "ground_truth_detail": {"method": "독극물"},
            "suspects": [{"suspect_id": 1, "name": "한지수"}],
            "clues": [{"id": 1, "name": "찻잔"}],
        }


class FakeRAGService:
    def __init__(self, matches=None):
        self.matches = matches or []
        self.indexed_fact = None

    async def find_self_info_facts(self, **kwargs):
        return self.matches

    async def index_fact(self, db, fact):
        self.indexed_fact = fact


class FakeLLMClient:
    def complete(self, *args, **kwargs):
        raise NotImplementedError

    async def acomplete(self, *args, **kwargs):
        raise NotImplementedError


class FakeFactGenerator:
    def __init__(self):
        self.seen_scenario = None

    async def agenerate_global_fact(self, *, scenario, suspect, wonder):
        self.seen_scenario = scenario
        return GeneratedGlobalFact(
            text=f"{suspect['name']}는 사건 전날 검은 우산을 잃어버렸다.",
            reasoning="기존 단서와 범행 방법을 바꾸지 않는 배경 정보다.",
        )


class FakeDB:
    def __init__(self):
        self.added = None
        self.flushed = False
        self.committed = False

    def add(self, obj):
        self.added = obj

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    def begin_nested(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


def _suspect() -> SuspectSchema:
    return SuspectSchema(
        suspect_id=1,
        name="한지수",
        role="연구원",
        age=32,
        gender="여성",
        description="침착한 연구원",
        is_culprit=False,
        motive=None,
        alibi_summary="사건 당시 휴게실에 있었다고 주장한다.",
        facts=[
            FactSchema(
                fact_id=1,
                threshold=0,
                type="timeline",
                content={
                    "time": "21:00-21:30",
                    "location": "휴게실",
                    "activity": "차를 마셨다",
                },
            )
        ],
        personality=PersonalitySchema(
            speech_style="존댓말",
            emotional_tendency="침착함",
            lying_pattern="deny",
        ),
    )


@pytest.mark.asyncio
async def test_fact_generation_graph_returns_existing_fact():
    existing = SimpleNamespace(
        fact_id=7,
        type="timeline",
        content={
            "time": "21:00-21:30",
            "location": "휴게실",
            "activity": "차를 마셨다",
        },
    )
    graph = FactGenerationGraph(
        scenario_repository=FakeScenarioRepository(),
        rag_service=FakeRAGService(matches=[existing]),
        llm_client=FakeLLMClient(),
    )

    result = await graph.aresolve(
        db=object(),
        scenario_id=1,
        suspect_id=1,
        suspect=_suspect(),
        wonder="내가 그 시간에 어디 있었지?",
    )

    assert result.fact_id == 7
    assert result.created is False
    assert result.source == "timeline"
    assert "휴게실" in result.text


@pytest.mark.asyncio
async def test_fact_generation_graph_creates_global_fact_and_updates_rag(monkeypatch):
    rag = FakeRAGService()
    graph = FactGenerationGraph(
        scenario_repository=FakeScenarioRepository(),
        rag_service=rag,
        llm_client=FakeLLMClient(),
    )
    fake_generator = FakeFactGenerator()
    graph.fact_generator = fake_generator

    async def fake_next_fact_id(db, scenario_id):
        return 42

    monkeypatch.setattr(graph, "_next_fact_id", fake_next_fact_id)
    db = FakeDB()

    result = await graph.aresolve(
        db=db,
        scenario_id=1,
        suspect_id=1,
        suspect=_suspect(),
        wonder="내 우산은 어디에 있었지?",
    )

    assert result.fact_id == 42
    assert result.created is True
    assert result.source == "global"
    assert db.added is rag.indexed_fact
    assert db.flushed is True
    assert db.committed is True
    assert db.added.suspect_id == 0
    assert db.added.content["source"] == "suspect_self_info_tool"
    assert fake_generator.seen_scenario["ground_truth_detail"]["method"] == "독극물"
