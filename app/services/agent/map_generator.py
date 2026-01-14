import json
import time
from typing import Type, TypeVar

from pydantic import BaseModel

from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema
from app.models.schemas.map import MapOutputSchema, MapSkeletonSchema

T = TypeVar("T", bound=BaseModel)


class MapGenerator:
    """Map 생성기 - 두 단계(Skeleton, Detail)로 분리"""

    def __init__(self, llm_client):
        self.llm = llm_client
        self.skeleton_prompt = PromptLoader.load("app/prompts/map/skeleton.txt")
        self.detail_prompt = PromptLoader.load("app/prompts/map/detail.txt")

    def _generate_with_prompt(
        self,
        user_input: dict | str,
        response_model: Type[T],
        system_prompt: str
    ) -> T:
        """지정된 프롬프트로 LLM 호출"""
        user_str = user_input
        if isinstance(user_input, dict):
            user_str = json.dumps(user_input, indent=2, ensure_ascii=False)

        raw_response = self.llm.complete(
            system=system_prompt,
            user=user_str,
            response_schema=response_model.model_json_schema()
        )

        json_text = extract_json(raw_response)
        data_dict = safe_json_load(json_text)

        time.sleep(3)  # Prevent API rate limit
        return response_model.model_validate(data_dict)

    def generate_skeleton(self, scenario: ScenarioExpansion) -> MapSkeletonSchema:
        """
        1단계: 방 구조 + 복도 + 위치 관계 생성
        """
        skeleton_input = self._extract_skeleton_input(scenario)
        return self._generate_with_prompt(
            skeleton_input,
            MapSkeletonSchema,
            self.skeleton_prompt
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
        return self._generate_with_prompt(
            detail_input,
            MapOutputSchema,
            self.detail_prompt
        )

    def _extract_skeleton_input(self,
                                scenario: ScenarioExpansion) -> dict:
        """Skeleton 생성을 위한 입력 추출"""
        return {
            "meta": scenario.meta.model_dump(mode='json'),
            "incident": scenario.incident.model_dump(mode='json'),
            "world": {
                "locations": scenario.world.locations,
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
