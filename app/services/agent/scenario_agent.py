import time
from typing import Dict, Any
import time

from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.scenario import (
    ScenarioSkeleton, 
    ScenarioExpansion, 
    ScenarioExpansionRequest,
    ExpansionPart1,
    ExpansionPart2
)


class ScenarioAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.case_prompt = PromptLoader.load(
            "app/prompts/scenario/case.txt"
        )
        self.skeleton_prompt = PromptLoader.load(
            "app/prompts/scenario/skeleton.txt"
        )
        self.expansion_prompt = PromptLoader.load(
            "app/prompts/scenario/expansion.txt"
        )

    def generate_case(self,
                      theme: str = "random") -> str:
        """
        Generates a narrative case synopsis based on the theme.
        """
        user_prompt = f"Please generate a mystery case synopsis. Theme: {theme}"
        raw_response = self.llm.complete(
            system=self.case_prompt,
            user=user_prompt,
        )
        
        return raw_response

    def generate_skeleton(self,
                          case: str) -> ScenarioSkeleton:
        """
        Generates a scenario skeleton based on the provided case synopsis.
        Injects the case synopsis into incident.summary.
        """
        raw_response = self.llm.complete(
            system=self.skeleton_prompt,
            user=case,
            response_schema=ScenarioSkeleton.model_json_schema()
        )

        json_text = extract_json(raw_response)
        data_dict = safe_json_load(json_text)
        
        # Inject the original case text into the summary
        if 'incident' in data_dict:
            data_dict['incident']['summary'] = case
        
        return ScenarioSkeleton.model_validate(data_dict)

    def generate_expansion(self,
                          skeleton: ScenarioSkeleton) -> ScenarioExpansion:
        """
        Generates detailed scenario elements from the skeleton using chunked generation.
        """
        skeleton_json = skeleton.model_dump_json(indent=2)
        
        # --- Part 1: World & Ground Truth ---
        raw_response_1 = self.llm.complete(
            system=self.expansion_prompt + "\n\nFocus on: world_detail, ground_truth_detail",
            user=skeleton_json,
            response_schema=ExpansionPart1.model_json_schema()
        )
        json_text_1 = extract_json(raw_response_1)
        data_part_1 = safe_json_load(json_text_1)
        time.sleep(3)

        # --- Part 2: Targets & Constraints ---
        raw_response_2 = self.llm.complete(
            system=self.expansion_prompt + "\n\nFocus on: generation_targets, constraints",
            user=skeleton_json,
            response_schema=ExpansionPart2.model_json_schema()
        )
        json_text_2 = extract_json(raw_response_2)
        data_part_2 = safe_json_load(json_text_2)
        time.sleep(3)

        # --- Merge Logic ---
        skeleton_dict = skeleton.model_dump()
        final_data = skeleton_dict.copy()

        # Merge Part 1 Data
        # World
        world_detail = skeleton_dict['world'].copy()
        if 'world_detail' in data_part_1:
            world_detail.update(data_part_1['world_detail'])
        final_data['world_detail'] = world_detail

        # Ground Truth
        gt_detail = skeleton_dict['ground_truth'].copy()
        if 'ground_truth_detail' in data_part_1:
            gt_detail.update(data_part_1['ground_truth_detail'])
        final_data['ground_truth_detail'] = gt_detail

        # Merge Part 2 Data
        final_data['generation_targets'] = data_part_2.get('generation_targets')
        final_data['constraints'] = data_part_2.get('constraints')

        return ScenarioExpansion.model_validate(final_data)
