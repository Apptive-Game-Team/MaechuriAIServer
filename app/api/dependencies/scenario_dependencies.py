from app.services.scenario.scenario_service import ScenarioService
from app.services.scenario.solve_service import SolveService
from app.services.llm.gemini_client import GeminiClient


def get_scenario_service() -> ScenarioService:
    """Provide ScenarioService with GeminiClient as default LLM."""
    llm_client = GeminiClient()
    return ScenarioService(llm_client)


def get_solve_service() -> SolveService:
    """Provide SolveService with GeminiClient as default LLM."""
    llm_client = GeminiClient()
    return SolveService(llm_client)
