from app.services.scenario.scenario_service import ScenarioService


def get_scenario_service() -> ScenarioService:
    return ScenarioService()
