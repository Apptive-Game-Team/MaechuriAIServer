import json

import pytest

from app.models.domain.suspect_state import SuspectState
from app.models.schemas.suspect import FactSchema, PersonalitySchema, SuspectSchema
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.suspect_actor_tools import (
    SuspectActorTool,
    SuspectActorToolSet,
    SuspectToolResult,
)


class FakeLLMClient:
    def __init__(self):
        self.calls = []

    def complete(self, *args, **kwargs):
        raise NotImplementedError

    async def acomplete(self, system, user="", response_schema=None, max_output_tokens=None):
        self.calls.append(
            {
                "system": system,
                "user": user,
                "schema": response_schema,
            }
        )
        if len(self.calls) == 1:
            return json.dumps(
                {
                    "action": "use_tool",
                    "tool_name": "resolve_self_info",
                    "tool_args": {"wonder": "잃어버린 우산"},
                    "pressure_delta": 0,
                    "reasoning": "자기 정보 확인이 필요한 질문이다.",
                    "detected_strategy": "sympathy",
                    "is_critical_hit": False,
                    "response": "",
                },
                ensure_ascii=False,
            )
        assert "[RESOLVED SELF INFO - canonical scenario fact]" in system
        return json.dumps(
                {
                    "pressure_delta": 0,
                    "reasoning": "확인된 자기 정보를 바탕으로 답한다.",
                    "detected_strategy": "sympathy",
                    "is_critical_hit": False,
                    "response": "그 우산이라면 사건 전날 잃어버렸습니다.",
                    "action": "respond",
                    "tool_name": None,
                    "tool_args": {},
                },
                ensure_ascii=False,
            )


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
async def test_suspect_actor_calls_self_info_tool_before_final_response():
    llm = FakeLLMClient()
    actor = SuspectActor(llm)
    tool_calls = []

    async def resolve_self_info(args: dict) -> SuspectToolResult:
        tool_calls.append(args)
        return SuspectToolResult(
            name="resolve_self_info",
            content="한지수는 사건 전날 검은 우산을 잃어버렸다.",
            metadata={"fact_id": 42, "source": "global", "created": True},
        )

    result = await actor.arespond(
        user_message="당신 우산은 어디에 있었죠?",
        suspect=_suspect(),
        state=SuspectState(suspect_id=1, current_pressure=0),
        knowledge_context="",
        tools=SuspectActorToolSet(
            [
                SuspectActorTool(
                    name="resolve_self_info",
                    description="Find or create self-info fact.",
                    handler=resolve_self_info,
                    format_context=lambda result: (
                        "[RESOLVED SELF INFO - canonical scenario fact]\n"
                        f"- {result.content}"
                    ),
                )
            ]
        ),
    )

    assert tool_calls == [{"wonder": "잃어버린 우산"}]
    assert result.response == "그 우산이라면 사건 전날 잃어버렸습니다."
    assert len(llm.calls) == 2
