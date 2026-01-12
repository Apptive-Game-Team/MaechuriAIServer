from app.services.agent.base_generator import BaseGenerator
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema


class ClueGenerator(BaseGenerator):
    def __init__(self, llm_client):
        system_prompt = PromptLoader.load(
            "app/prompts/clue/generation.txt"
        )
        super().__init__(llm_client, system_prompt)

    def generate_clues(self, scenario: ScenarioExpansion) -> ClueSetSchema:
        """
        Generates clues based on the provided ScenarioExpansion.
        """
        # Optimize Input: Select only necessary fields
        optimized_input = {
            "world": scenario.world_detail.model_dump(mode='json'),
            "crime": scenario.ground_truth_detail.model_dump(mode='json'),
            "target": scenario.generation_targets.evidence.model_dump(mode='json')
        }

        return self._generate(optimized_input, ClueSetSchema)
