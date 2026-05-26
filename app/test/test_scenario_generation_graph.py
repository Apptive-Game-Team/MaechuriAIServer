from app.services.scenario.scenario_generation_graph import ScenarioGenerationGraph


class FakeScenarioGenerator:
    def generate_case(self, pre_input: str) -> str:
        return f"case:{pre_input}"


class FakeScenarioService:
    def __init__(self):
        self.calls = []
        self.scenario_generator = FakeScenarioGenerator()

    def _load_or_generate(
        self,
        request_id,
        step_name,
        generator_func,
        schema_name,
        model_type=None,
        use_retry=True,
        generator=None,
    ):
        self.calls.append(("load_or_generate", request_id, step_name, schema_name))
        return generator_func(), True

    def _sleep_if_generated(self, was_generated: bool, seconds: float = 3):
        self.calls.append(("sleep", was_generated, seconds))

    def _generate_and_validate_expansion(self, case_state: str, request_id: str):
        self.calls.append(("generate_expansion", case_state, request_id))
        return {"case_state": case_state}

    def _generate_content_with_clearability_check(
        self,
        expansion_result,
        request_id: str,
    ):
        self.calls.append(("generate_content", expansion_result, request_id))
        return {"scenario": expansion_result}


def test_scenario_generation_graph_runs_pipeline_in_order():
    service = FakeScenarioService()
    graph = ScenarioGenerationGraph(service)

    result = graph.invoke("locked-room", "request-1")

    assert result == {"scenario": {"case_state": "case:locked-room"}}
    assert service.calls == [
        ("load_or_generate", "request-1", "case_state", "CaseState"),
        ("sleep", True, 3),
        ("generate_expansion", "case:locked-room", "request-1"),
        ("generate_content", {"case_state": "case:locked-room"}, "request-1"),
    ]
