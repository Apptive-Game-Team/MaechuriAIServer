import json
import time
from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema


class ClueGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.generation_prompt = PromptLoader.load(
            "app/prompts/clue/generation.txt"
        )

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

        # Pass the optimized JSON to the LLM
        raw_response = self.llm.complete(
            system=self.generation_prompt,
            user=json.dumps(optimized_input, indent=2, ensure_ascii=False),
            response_schema=ClueSetSchema.model_json_schema()
        )

        json_text = extract_json(raw_response)
        data_dict = safe_json_load(json_text)

        time.sleep(3)  # Prevent API rate limit
        return ClueSetSchema.model_validate(data_dict)
