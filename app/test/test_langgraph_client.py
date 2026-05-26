import asyncio

from app.services.llm.langgraph_client import (
    LangGraphLLMClient,
    ensure_langgraph_llm_client,
)
from app.services.llm.llm_client import LLMClient


class FakeLLMClient(LLMClient):
    def __init__(self):
        self.sync_calls = []
        self.async_calls = []

    def complete(
        self,
        system: str,
        user: str = "",
        response_schema: dict | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        self.sync_calls.append(
            {
                "system": system,
                "user": user,
                "response_schema": response_schema,
                "max_output_tokens": max_output_tokens,
            }
        )
        return "sync-response"

    async def acomplete(
        self,
        system: str,
        user: str = "",
        response_schema: dict | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        self.async_calls.append(
            {
                "system": system,
                "user": user,
                "response_schema": response_schema,
                "max_output_tokens": max_output_tokens,
            }
        )
        return "async-response"


def test_langgraph_llm_client_delegates_sync_completion():
    delegate = FakeLLMClient()
    client = LangGraphLLMClient(delegate)
    schema = {"type": "object"}

    response = client.complete(
        system="system",
        user="user",
        response_schema=schema,
        max_output_tokens=123,
    )

    assert response == "sync-response"
    assert delegate.sync_calls == [
        {
            "system": "system",
            "user": "user",
            "response_schema": schema,
            "max_output_tokens": 123,
        }
    ]


def test_langgraph_llm_client_delegates_async_completion():
    delegate = FakeLLMClient()
    client = LangGraphLLMClient(delegate)
    schema = {"type": "object"}

    response = asyncio.run(
        client.acomplete(
            system="system",
            user="user",
            response_schema=schema,
            max_output_tokens=456,
        )
    )

    assert response == "async-response"
    assert delegate.async_calls == [
        {
            "system": "system",
            "user": "user",
            "response_schema": schema,
            "max_output_tokens": 456,
        }
    ]


def test_ensure_langgraph_llm_client_does_not_double_wrap():
    wrapped = LangGraphLLMClient(FakeLLMClient())

    assert ensure_langgraph_llm_client(wrapped) is wrapped
