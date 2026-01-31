from app.services.prompt.prompt_loader import PromptLoader
from app.services.agent.base_generator import BaseGenerator
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema
from app.models.schemas.map import MapOutputSchema, MapSkeletonSchema


class MapGenerator(BaseGenerator):
    """Map 생성기 - 두 단계(Skeleton, Detail)로 분리"""

    def __init__(self, llm_client):
        self.skeleton_prompt = PromptLoader.load("app/prompts/map/skeleton.txt")
        self.detail_prompt = PromptLoader.load("app/prompts/map/detail.txt")
        super().__init__(llm_client, self.skeleton_prompt)

    def generate_skeleton(self, scenario: ScenarioExpansion) -> MapSkeletonSchema:
        """
        1단계: 방 구조 + 복도 + 위치 관계 생성
        """
        skeleton_input = self._extract_skeleton_input(scenario)
        return self._generate(
            skeleton_input,
            MapSkeletonSchema,
            system_prompt=self.skeleton_prompt
        )

    def generate_detail(
        self,
        scenario: ScenarioExpansion,
        skeleton: MapSkeletonSchema,
        clues: ClueSetSchema
    ) -> MapOutputSchema:
        """
        2단계: 오브젝트 배치 + 상세 정보
        """
        detail_input = self._extract_detail_input(scenario, skeleton, clues)
        return self._generate(
            detail_input,
            MapOutputSchema,
            system_prompt=self.detail_prompt
        )

    def _extract_skeleton_input(self,
                                scenario: ScenarioExpansion) -> dict:
        """Skeleton 생성을 위한 입력 추출"""
        visibility_rules = scenario.world_detail.visibility_rules or []
        access_rules = scenario.world_detail.access_rules or []
        return {
            "meta": scenario.meta.model_dump(mode='json'),
            "incident": scenario.incident.model_dump(mode='json'),
            "world": {
                "locations": scenario.world_detail.locations,
                "visibility_rules": [x.model_dump(mode='json') for x in visibility_rules],
                "access_rules": [x.model_dump(mode='json') for x in access_rules],
                "time_granularity_minutes": scenario.world.time_granularity_minutes,
            },
        }

    def _extract_detail_input(
        self,
        scenario: ScenarioExpansion,
        skeleton: MapSkeletonSchema,
        clues: ClueSetSchema
    ) -> dict:
        """Detail 생성을 위한 입력 추출"""
        return {
            "meta": scenario.meta.model_dump(mode='json'),
            "map_skeleton": skeleton.model_dump(mode='json'),
            "clues": {
                "clues": [
                    {
                        "name": c.name,
                        "found_at": c.found_at,
                        "is_red_herring": c.is_red_herring
                    }
                    for c in clues.clues
                ]
            },
            "generation_targets": scenario.generation_targets.model_dump(mode='json'),
        }
