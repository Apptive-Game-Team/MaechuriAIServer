import json
from asyncio.windows_events import NULL
from typing import Dict, Any

from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.scenario import ScenarioSkeleton, ScenarioExpansion


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
        평서문 형태로 사건의 대략적인 내용을 서술합니다.
        :param theme: 사건의 중심이 되는 키워드 또는 원하는 방향성을 제시한 파라미터
        :return: 평서문 str
        """
        user_prompt = self._build_user_prompt(theme)
        raw_response = self.llm.complete(
            system=self.case_prompt,
            user=user_prompt,
        )

        return raw_response
    def generate_skeleton(self,
                          case: str = "random") -> ScenarioSkeleton:
        """
        Generates a scenario skeleton based on the provided theme.
        """
        raw_response = self.llm.complete(
            system=self.skeleton_prompt,
            user=case,
        )

        json_text = self._extract_json(raw_response)
        data_dict = self._safe_json_load(json_text)

        # case에 대한 내용 강제 주입
        if "incident" in data_dict:
            data_dict["incident"]["summary"] = case
        
        return ScenarioSkeleton.model_validate(data_dict)

    def generate_expansion(self,
                          skeleton: ScenarioSkeleton) -> ScenarioExpansion:
        """
        스켈레톤 파이썬 코드로부터 디테일한 요소를 만들어냅니다.
        :param skeleton: 스켈레톤 시나리오 객체
        :return: expansion scenario
        """
        # 1. LLM에게 스켈레톤 정보를 제공하여 확장을 요청
        raw_response = self.llm.complete(
            system=self.expansion_prompt,
            user=skeleton.model_dump_json(indent=2)
        )

        json_text = self._extract_json(raw_response)
        new_data = self._safe_json_load(json_text)

        # 2. 스켈레톤 데이터(기존)와 확장 데이터(신규) 병합
        skeleton_dict = skeleton.model_dump()
        final_data = skeleton_dict.copy()

        # World: Skeleton의 world 정보를 가져와서 world_detail로 확장
        # world_detail은 WorldSkeletonSchema를 상속받으므로 locations 정보가 필요함
        world_detail = skeleton_dict['world'].copy()
        if 'world_detail' in new_data:
            world_detail.update(new_data['world_detail'])
        final_data['world_detail'] = world_detail

        # Ground Truth: Skeleton의 ground_truth 정보를 가져와서 ground_truth_detail로 확장
        # ground_truth_detail은 GroundTruthSkeletonSchema를 상속받으므로 culprit_count 등이 필요함
        gt_detail = skeleton_dict['ground_truth'].copy()
        if 'ground_truth_detail' in new_data:
            gt_detail.update(new_data['ground_truth_detail'])
        final_data['ground_truth_detail'] = gt_detail

        # 나머지 신규 필드 추가
        final_data['generation_targets'] = new_data.get('generation_targets')
        final_data['constraints'] = new_data.get('constraints')

        return ScenarioExpansion.model_validate(final_data)

    def _build_user_prompt(self, theme: str) -> str:
        return f"Please generate a highly detailed mystery scenario in plain, descriptive sentences. Theme: {theme}"

    def _extract_json(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                f"LLM output is incomplete JSON:\n{text}"
            )

        return text[start:end + 1]

    def _safe_json_load(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Simple repair for common LLM JSON issues
            repaired = (
                text.replace("True", "true")
                .replace("False", "false")
                .replace("None", "null")
            )
            return json.loads(repaired)
