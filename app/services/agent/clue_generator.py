from typing import Optional

from app.services.agent.base_generator import BaseGenerator
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema
from app.models.schemas.map import MapSkeletonSchema


class ClueGenerator(BaseGenerator):
    def __init__(self, llm_client):
        system_prompt = PromptLoader.load(
            "app/prompts/clue/generation.txt"
        )
        super().__init__(llm_client, system_prompt)

    def generate_clues(
        self,
        scenario: ScenarioExpansion,
        map_skeleton: Optional[MapSkeletonSchema] = None
    ) -> ClueSetSchema:
        """
        Generates clues based on the provided ScenarioExpansion and optional MapSkeletonSchema.
        """
        # Optimize Input: Select only necessary fields
        optimized_input = {
            "world": scenario.world_detail.model_dump(mode='json'),
            "crime": scenario.ground_truth_detail.model_dump(mode='json'),
            "target": scenario.generation_targets.evidence.model_dump(mode='json')
        }

        # Add map skeleton if provided
        if map_skeleton:
            optimized_input["map_skeleton"] = map_skeleton.model_dump(mode='json')

        return self._generate(optimized_input, ClueSetSchema)
