from typing import Optional

from app.services.agent.base_generator import BaseGenerator
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas import ClueSetSchema
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
        map_skeleton: Optional[MapSkeletonSchema] = None,
        clearability_feedback: str = "",
    ) -> ClueSetSchema:
        """Generate clues based on the ScenarioExpansion and optional MapSkeletonSchema.

        Parameters
        ----------
        scenario : ScenarioExpansion
            The scenario expansion with case/world/ground truth context.
        map_skeleton : MapSkeletonSchema, optional
            Map layout for location-aware clue placement.
        clearability_feedback : str
            If non-empty, feedback from a previous clearability failure
            to guide clue generation fixes.
        """
        # Prepare prompt context
        prompt_data = {
            "case_context": scenario.incident.model_dump(mode='json'),
            "world_context": scenario.world_detail.model_dump(mode='json'),
            "target": scenario.generation_targets.clues.model_dump(mode='json')
        }

        # Add map skeleton if provided
        if map_skeleton:
            prompt_data["map_skeleton"] = map_skeleton.model_dump(mode='json')

        # Inject clearability feedback if this is a retry
        if clearability_feedback:
            prompt_data["clearability_feedback"] = (
                "[CLEARABILITY FIX — PREVIOUS ATTEMPT FAILED]\n"
                f"The previous generation failed clearability evaluation:\n"
                f"{clearability_feedback}\n\n"
                "You MUST address these issues:\n"
                "- Ensure clues cover all 4 deduction axes: WHO, HOW, WHY, WHEN\n"
                "- Reduce the number of red herring clues if too many obscure the path\n"
                "- Make critical clues (pointing to culprit) accessible in early locations\n"
                "- Ensure at least one clear deductive chain exists within 20 turns"
            )

        return self._generate(prompt_data, ClueSetSchema)
