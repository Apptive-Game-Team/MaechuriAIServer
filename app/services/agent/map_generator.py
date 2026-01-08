from app.services.agent.base_generator import BaseGenerator
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema
from app.models.schemas.map import MapOutputSchema


class MapGenerator(BaseGenerator):
    def __init__(self, llm_client):
        system_prompt = PromptLoader.load("app/prompts/map/generation.txt")
        super().__init__(llm_client, system_prompt)

    def generate_map(self,
                     scenario: ScenarioExpansion,
                     clues: ClueSetSchema) -> MapOutputSchema:
        """
        Generates a map based on the provided ScenarioExpansion and ClueSetSchema.
        """
        # Prepare input
        full_data = scenario.model_dump(mode='json')
        full_data['clues'] = clues.model_dump(mode='json')
        
        map_input = self._extract_map_generator_input(full_data)
        
        return self._generate(map_input, MapOutputSchema)

    def _extract_map_generator_input(self, p: dict) -> dict:
        """
        시나리오 전체 JSON(p)에서
        map_generator에 필요한 '필드 단위 정보'만
        값 변경 없이 그대로 추출한다.
        """
        return {
            # 분위기 / 난이도 / 톤
            "meta": p.get("meta"),

            # 공간의 존재 자체 (이름 목록)
            "world": {
                "locations": p.get("world", {}).get("locations"),
                "time_granularity_minutes": p.get("world", {}).get("time_granularity_minutes"),
            },

            # 시야 / 접근 / 증거 타입 규칙
            "world_detail": {
                "visibility_rules": p.get("world_detail", {}).get("visibility_rules"),
                "access_rules": p.get("world_detail", {}).get("access_rules"),
                "evidence_types": p.get("world_detail", {}).get("evidence_types"),
            },

            # suspect / evidence 생성 파라미터
            "generation_targets": p.get("generation_targets"),

            # 단서의 '위치와 성격' 정보만
            "clues": {
                "clues": [
                    {
                        "name": c.get("name"),
                        "found_at": c.get("found_at"),
                        "is_red_herring": c.get("is_red_herring")
                    }
                    for c in p.get("clues", {}).get("clues", [])
                ]
            },

            # 세계 제약 조건
            "constraints": p.get("constraints"),
        }
