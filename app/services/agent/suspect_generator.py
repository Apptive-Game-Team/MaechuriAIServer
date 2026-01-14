import json
import time
from typing import List

from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.suspect import (
    SuspectGenerationRequest,
    SuspectListSchema,
    SuspectSchema
)


class SuspectGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load(
            "app/prompts/suspect/system.txt"
        )
        self.build_prompt = PromptLoader.load(
            "app/prompts/suspect/build.txt"
        )

    def generate(self, request: SuspectGenerationRequest) -> SuspectListSchema:
        """
        용의자를 1명씩 청크 단위로 생성하여 결과를 합침.

        Args:
            request: 용의자 생성 요청

        Returns:
            SuspectListSchema: 생성된 용의자 목록
        """
        suspect_count = request.generation_config.count
        culprit_ids = request.ground_truth.culprit_ids

        suspects: List[SuspectSchema] = []

        for i in range(suspect_count):
            suspect_id = i + 1
            is_culprit = suspect_id in culprit_ids

            print(f"Generating suspect {suspect_id}/{suspect_count} (culprit: {is_culprit})...")

            # 단일 용의자 생성 시도 (최대 3회)
            suspect = None
            for attempt in range(3):
                try:
                    suspect = self._generate_single(
                        request=request,
                        suspect_id=suspect_id,
                        is_culprit=is_culprit,
                        already_generated=suspects
                    )
                    break
                except Exception as e:
                    print(f"  Attempt {attempt + 1} failed: {e}")
                    time.sleep(2)

            if suspect is None:
                raise RuntimeError(f"Failed to generate suspect {suspect_id}")

            suspects.append(suspect)
            print(f"  Suspect {suspect_id} ({suspect.name}) generated successfully")

            # API 속도 조절 (마지막 제외)
            if i < suspect_count - 1:
                time.sleep(2)

        return SuspectListSchema(suspects=suspects)

    def _generate_single(
        self,
        request: SuspectGenerationRequest,
        suspect_id: int,
        is_culprit: bool,
        already_generated: List[SuspectSchema]
    ) -> SuspectSchema:
        """
        단일 용의자 생성.

        Args:
            request: 원본 요청
            suspect_id: 생성할 용의자 ID
            is_culprit: 범인 여부
            already_generated: 이미 생성된 용의자들 (중복 방지용)

        Returns:
            SuspectSchema: 생성된 용의자
        """
        prompt = self._build_single_prompt(
            request=request,
            suspect_id=suspect_id,
            is_culprit=is_culprit,
            already_generated=already_generated
        )

        # 단일 용의자 스키마로 요청
        single_schema = SuspectSchema.model_json_schema()

        raw = self.llm.complete(
            system=self.system_prompt,
            user=prompt,
            response_schema=single_schema
        )

        json_text = extract_json(raw)
        data = safe_json_load(json_text)

        return SuspectSchema.model_validate(data)

    def _build_single_prompt(
        self,
        request: SuspectGenerationRequest,
        suspect_id: int,
        is_culprit: bool,
        already_generated: List[SuspectSchema]
    ) -> str:
        """단일 용의자 생성용 프롬프트 구성"""

        # 이미 생성된 용의자 정보 요약
        existing_summary = []
        for s in already_generated:
            existing_summary.append({
                "suspect_id": s.suspect_id,
                "name": s.name,
                "role": s.role,
                "is_culprit": s.is_culprit
            })

        single_instruction = f"""
{self.build_prompt}

[SINGLE SUSPECT GENERATION]
You must generate EXACTLY ONE suspect with the following requirements:
- suspect_id: {suspect_id}
- is_culprit: {is_culprit}

[ALREADY GENERATED SUSPECTS]
{json.dumps(existing_summary, ensure_ascii=False, indent=2) if existing_summary else "None yet"}

[IMPORTANT]
- Do NOT duplicate names or roles from already generated suspects
- Return a SINGLE suspect object (not a list)
- The suspect_id MUST be {suspect_id}
- is_culprit MUST be {is_culprit}
"""

        return json.dumps({
            "input": request.model_dump(mode='json'),
            "instruction": single_instruction,
        }, ensure_ascii=False)

    def _build_prompt(self, request: SuspectGenerationRequest) -> str:
        """전체 생성용 프롬프트 (레거시, 미사용)"""
        return json.dumps({
            "input": request.model_dump(mode='json'),
            "instruction": self.build_prompt,
        }, ensure_ascii=False)
