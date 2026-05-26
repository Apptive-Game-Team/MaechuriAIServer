from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.utils import extract_json, safe_json_load
from app.services.agent.suspect_actor_tools import (
    SuspectActorToolSet,
    SuspectToolResult,
)
from app.services.llm import ensure_langgraph_llm_client
from app.services.llm.llm_client import LLMClient
from app.services.prompt.prompt_loader import PromptLoader
from app.services.npc.formatters import ChatFormatter
from app.models.schemas.suspect import SuspectSchema
from app.models.schemas.suspect_responder import (
    SuspectActorOutput,
    SuspectAgentDecision,
)
from app.models.domain.suspect_state import SuspectState


class SuspectActorState(TypedDict, total=False):
    user_message: str
    suspect: SuspectSchema
    runtime_state: SuspectState
    clue_presented: Optional[dict]
    knowledge_context: str
    tool_context: str
    tool_call_count: int
    tools: Optional[SuspectActorToolSet]
    decision: SuspectAgentDecision
    tool_result: SuspectToolResult
    output: SuspectActorOutput


class SuspectActor:
    """
    Judge + Actor agent.

    The agent first decides whether it can answer from context or needs a tool.
    If it calls a tool, the final response is produced after the tool result is
    added to knowledge context.
    """

    MAX_TOOL_CALLS = 3

    def __init__(self, llm_client: LLMClient):
        self.llm = ensure_langgraph_llm_client(llm_client)
        self.system_prompt_template = PromptLoader.load("app/prompts/suspect_responder/system.txt")
        self.agent_graph = self._build_agent_graph()

    async def arespond(
        self,
        user_message: str,
        suspect: SuspectSchema,
        state: SuspectState,
        clue_presented: Optional[dict] = None,
        knowledge_context: str = "",
        tools: Optional[SuspectActorToolSet] = None,
    ) -> SuspectActorOutput:
        """Run the suspect actor agent.

        Args:
            user_message: Detective message
            suspect: Suspect schema data
            state: Current runtime state (pressure etc.)
            clue_presented: Clue being presented (if any)
            knowledge_context: Structured knowledge context from build_suspect_knowledge_context()
            tools: Tool callbacks the agent may invoke.

        Returns:
            SuspectActorOutput: pressure_delta + reasoning + response
        """
        result = await self.agent_graph.ainvoke(
            {
                "user_message": user_message,
                "suspect": suspect,
                "runtime_state": state,
                "clue_presented": clue_presented,
                "knowledge_context": knowledge_context or "",
                "tool_context": "",
                "tool_call_count": 0,
                "tools": tools,
            }
        )
        output = result.get("output")
        if output is None:
            raise RuntimeError("Suspect actor agent finished without output")
        return output

    def _build_agent_graph(self):
        builder = StateGraph(SuspectActorState)
        builder.add_node("decide", self._decide)
        builder.add_node("call_tool", self._call_tool)

        builder.add_edge(START, "decide")
        builder.add_conditional_edges(
            "decide",
            self._route_after_decision,
            {
                "respond": END,
                "tool": "call_tool",
            },
        )
        builder.add_edge("call_tool", "decide")
        return builder.compile()

    async def _decide(self, state: SuspectActorState) -> SuspectActorState:
        decision = await self._complete_decision(
            user_message=state["user_message"],
            suspect=state["suspect"],
            state=state["runtime_state"],
            clue_presented=state.get("clue_presented"),
            knowledge_context=self._build_effective_context(state),
            tools=state.get("tools"),
        )
        if (
            decision.action != "use_tool"
            or state.get("tool_call_count", 0) >= self.MAX_TOOL_CALLS
        ):
            return {
                "decision": decision,
                "output": self._decision_to_output(decision),
            }
        return {"decision": decision}

    @staticmethod
    def _route_after_decision(state: SuspectActorState) -> str:
        decision = state["decision"]
        tools = state.get("tools")
        if decision.action == "use_tool" and tools and tools.get(decision.tool_name):
            return "tool"
        return "respond"

    async def _call_tool(
        self,
        state: SuspectActorState,
    ) -> SuspectActorState:
        decision = state["decision"]
        tools = state["tools"]
        tool = tools.get(decision.tool_name) if tools else None
        if tool is None:
            return {"output": self._decision_to_output(decision)}

        tool_result = await tool.arun(decision.tool_args)
        tool_context = self._append_tool_result(
            state.get("tool_context", ""),
            tools,
            tool_result,
        )
        return {
            "tool_result": tool_result,
            "tool_context": tool_context,
            "tool_call_count": state.get("tool_call_count", 0) + 1,
        }

    async def _complete_decision(
        self,
        *,
        user_message: str,
        suspect: SuspectSchema,
        state: SuspectState,
        clue_presented: Optional[dict],
        knowledge_context: str,
        tools: Optional[SuspectActorToolSet],
    ) -> SuspectAgentDecision:
        knowledge_context = self._append_tool_descriptions(
            knowledge_context,
            tools,
        )
        prompt_data = ChatFormatter.build_suspect_prompt_data(
            suspect=suspect, state=state,
            clue_presented=clue_presented,
            knowledge_context=knowledge_context,
        )

        formatted_prompt = self.system_prompt_template.format(**prompt_data)

        raw = await self.llm.acomplete(
            system=formatted_prompt,
            user=user_message,
            response_schema=SuspectAgentDecision.model_json_schema()
        )

        json_text = extract_json(raw)
        data = safe_json_load(json_text)
        return SuspectAgentDecision.model_validate(data)

    @staticmethod
    def _decision_to_output(decision: SuspectAgentDecision) -> SuspectActorOutput:
        response = decision.response or "그 부분은 지금 정확히 기억나지 않습니다."
        return SuspectActorOutput(
            pressure_delta=decision.pressure_delta,
            reasoning=decision.reasoning,
            detected_strategy=decision.detected_strategy,
            is_critical_hit=decision.is_critical_hit,
            response=response,
        )

    def _build_effective_context(self, state: SuspectActorState) -> str:
        context = state.get("knowledge_context", "")
        tool_context = state.get("tool_context", "")
        if tool_context:
            context = f"{context}\n\n{tool_context}" if context else tool_context
        return context

    @staticmethod
    def _append_tool_descriptions(
        knowledge_context: str,
        tools: Optional[SuspectActorToolSet],
    ) -> str:
        tool_descriptions = tools.describe() if tools else ""
        if not tool_descriptions:
            return knowledge_context
        if not knowledge_context:
            return tool_descriptions
        return f"{knowledge_context}\n\n{tool_descriptions}"

    @staticmethod
    def _append_tool_result(
        knowledge_context: str,
        tools: Optional[SuspectActorToolSet],
        result: SuspectToolResult,
    ) -> str:
        section = (
            tools.format_result(result)
            if tools
            else f"[TOOL RESULT: {result.name}]\n{result.content}"
        )
        if not knowledge_context:
            return section
        return f"{knowledge_context}\n\n{section}"
