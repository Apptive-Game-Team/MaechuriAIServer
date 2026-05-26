from typing import TYPE_CHECKING, TypedDict

from langgraph.graph import END, START, StateGraph

from app.models.schemas.scenario import ScenarioExpansion, ScenarioResult

if TYPE_CHECKING:
    from app.services.scenario.scenario_service import ScenarioService


class ScenarioGenerationState(TypedDict, total=False):
    pre_input: str
    request_id: str
    case_state: str
    expansion_result: ScenarioExpansion
    final_scenario: ScenarioResult


class ScenarioGenerationGraph:
    """LangGraph orchestration for the scenario generation pipeline."""

    def __init__(self, service: "ScenarioService"):
        self.service = service
        self.graph = self._build_graph()

    def invoke(self, pre_input: str, request_id: str) -> ScenarioResult:
        state = self.graph.invoke(
            {
                "pre_input": pre_input,
                "request_id": request_id,
            }
        )
        final_scenario = state.get("final_scenario")
        if final_scenario is None:
            raise RuntimeError("Scenario generation graph finished without a result")
        return final_scenario

    def _build_graph(self):
        builder = StateGraph(ScenarioGenerationState)
        builder.add_node("generate_case", self._generate_case)
        builder.add_node("generate_expansion", self._generate_expansion)
        builder.add_node("generate_content", self._generate_content)

        builder.add_edge(START, "generate_case")
        builder.add_edge("generate_case", "generate_expansion")
        builder.add_edge("generate_expansion", "generate_content")
        builder.add_edge("generate_content", END)

        return builder.compile()

    def _generate_case(
        self, state: ScenarioGenerationState
    ) -> ScenarioGenerationState:
        request_id = state["request_id"]
        case_state, generated = self.service._load_or_generate(
            request_id,
            "case_state",
            lambda: self.service.scenario_generator.generate_case(
                state["pre_input"]
            ),
            "CaseState",
            use_retry=False,
        )
        self.service._sleep_if_generated(generated)
        return {"case_state": case_state}

    def _generate_expansion(
        self, state: ScenarioGenerationState
    ) -> ScenarioGenerationState:
        expansion_result = self.service._generate_and_validate_expansion(
            state["case_state"],
            state["request_id"],
        )
        return {"expansion_result": expansion_result}

    def _generate_content(
        self, state: ScenarioGenerationState
    ) -> ScenarioGenerationState:
        final_scenario = self.service._generate_content_with_clearability_check(
            state["expansion_result"],
            state["request_id"],
        )
        return {"final_scenario": final_scenario}
