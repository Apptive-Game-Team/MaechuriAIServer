from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.llm.llm_client import LLMClient


class LLMCompletionState(TypedDict, total=False):
    system: str
    user: str
    response_schema: dict[str, Any] | None
    max_output_tokens: int | None
    response: str


class LangGraphLLMClient(LLMClient):
    """LLMClient adapter that runs every completion through LangGraph."""

    def __init__(self, delegate: LLMClient):
        self.delegate = delegate
        self._sync_graph = self._build_sync_graph()
        self._async_graph = self._build_async_graph()

    def complete(
        self,
        system: str,
        user: str = "",
        response_schema: dict | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        state = self._sync_graph.invoke(
            {
                "system": system,
                "user": user,
                "response_schema": response_schema,
                "max_output_tokens": max_output_tokens,
            }
        )
        return state["response"]

    async def acomplete(
        self,
        system: str,
        user: str = "",
        response_schema: dict | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        state = await self._async_graph.ainvoke(
            {
                "system": system,
                "user": user,
                "response_schema": response_schema,
                "max_output_tokens": max_output_tokens,
            }
        )
        return state["response"]

    def _build_sync_graph(self):
        builder = StateGraph(LLMCompletionState)
        builder.add_node("complete", self._complete_node)
        builder.add_edge(START, "complete")
        builder.add_edge("complete", END)
        return builder.compile()

    def _build_async_graph(self):
        builder = StateGraph(LLMCompletionState)
        builder.add_node("acomplete", self._acomplete_node)
        builder.add_edge(START, "acomplete")
        builder.add_edge("acomplete", END)
        return builder.compile()

    def _complete_node(self, state: LLMCompletionState) -> LLMCompletionState:
        response = self.delegate.complete(
            system=state["system"],
            user=state.get("user", ""),
            response_schema=state.get("response_schema"),
            max_output_tokens=state.get("max_output_tokens"),
        )
        return {"response": response}

    async def _acomplete_node(
        self,
        state: LLMCompletionState,
    ) -> LLMCompletionState:
        response = await self.delegate.acomplete(
            system=state["system"],
            user=state.get("user", ""),
            response_schema=state.get("response_schema"),
            max_output_tokens=state.get("max_output_tokens"),
        )
        return {"response": response}


def ensure_langgraph_llm_client(llm_client: LLMClient) -> LLMClient:
    if isinstance(llm_client, LangGraphLLMClient):
        return llm_client
    return LangGraphLLMClient(llm_client)
