import json
import time
from typing import List

from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.suspect import (
    SuspectGenerationRequest,
    SuspectGenerationListSchema,
    SuspectGenerationSchema
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

    def generate(self, request: SuspectGenerationRequest) -> SuspectGenerationListSchema:
        """
        용의자를 1명씩 청크 단위로 생성하여 결과를 합침.

        Args:
            request: 용의자 생성 요청

        Returns:
            SuspectGenerationListSchema: 생성된 용의자 목록
        """
        suspect_count = request.generation_config.count
        culprit_ids = request.ground_truth.culprit_ids

        suspects: List[SuspectGenerationSchema] = []

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

        return SuspectGenerationListSchema(suspects=suspects)

    def _generate_single(
        self,
        request: SuspectGenerationRequest,
        suspect_id: int,
        is_culprit: bool,
        already_generated: List[SuspectGenerationSchema]
    ) -> SuspectGenerationSchema:
        """
        단일 용의자 생성.

        Args:
            request: 원본 요청
            suspect_id: 생성할 용의자 ID
            is_culprit: 범인 여부
            already_generated: 이미 생성된 용의자들 (중복 방지용)

        Returns:
            SuspectGenerationSchema: 생성된 용의자
        """
        prompt = self._build_single_prompt(
            request=request,
            suspect_id=suspect_id,
            is_culprit=is_culprit,
            already_generated=already_generated
        )

        # 단일 용의자 스키마로 요청
        single_schema = SuspectGenerationSchema.model_json_schema()

        raw = self.llm.complete(
            system=self.system_prompt,
            user=prompt,
            response_schema=single_schema
        )

        json_text = extract_json(raw)
        data = safe_json_load(json_text)

        return SuspectGenerationSchema.model_validate(data)

    def _build_single_prompt(
        self,
        request: SuspectGenerationRequest,
        suspect_id: int,
        is_culprit: bool,
        already_generated: List[SuspectGenerationSchema]
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

        # Map skeleton 정보 요약 (있는 경우)
        map_info = ""
        if request.map_skeleton:
            room_names = [r.name for r in request.map_skeleton.rooms]
            corridor_info = [
                f"{c.name}: connects {[conn.room_id for conn in c.connections]}"
                for c in request.map_skeleton.corridors
            ]
            map_info = f"""

[MAP SKELETON]
Available rooms: {room_names}
Corridors: {corridor_info}
- Use this information to generate realistic timelines considering room accessibility
"""

        single_instruction = f"""
{self.build_prompt}

[SINGLE SUSPECT GENERATION]
You must generate EXACTLY ONE suspect with the following requirements:
- suspect_id: {suspect_id}
- is_culprit: {is_culprit}

[ALREADY GENERATED SUSPECTS]
{json.dumps(existing_summary, ensure_ascii=False, indent=2) if existing_summary else "None yet"}
{map_info}
[IMPORTANT]
- Do NOT duplicate names or roles from already generated suspects
- Return a SINGLE suspect object (not a list)
- The suspect_id MUST be {suspect_id}
- is_culprit MUST be {is_culprit}
"""

        # Exclude map_skeleton from JSON dump to avoid duplication
        request_data = request.model_dump(mode='json', exclude={'map_skeleton'})

        return json.dumps({
            "input": request_data,
            "instruction": single_instruction,
        }, ensure_ascii=False)

    def _build_prompt(self, request: SuspectGenerationRequest) -> str:
        """전체 생성용 프롬프트 (레거시, 미사용)"""
        return json.dumps({
            "input": request.model_dump(mode='json'),
            "instruction": self.build_prompt,
        }, ensure_ascii=False)
