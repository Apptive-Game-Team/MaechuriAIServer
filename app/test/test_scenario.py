from app.services.agent.scenario_agent import ScenarioAgent
from app.services.scenario.scenario_service import ScenarioService

if __name__ == "__main__":

    print("SCENARIO TEST")

    agent = ScenarioService()

    test_dict = agent.generate("온천에서 발생한 일")

    print(test_dict)