from app.services.scenario.scenario_service import ScenarioService
from app.services.llm.gemini_client import GeminiClient


def get_scenario_service() -> ScenarioService:
    """Provide ScenarioService with GeminiClient as default LLM."""
    llm_client = GeminiClient()
    return ScenarioService(llm_client)
