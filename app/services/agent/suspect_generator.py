import json
import time
import logging
from typing import List

from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
from app.models.schemas.suspect import (
    SuspectGenerationRequest,
    SuspectGenerationListSchema,
    SuspectGenerationSchema
)

logger = logging.getLogger(__name__)

# Generate suspects in batches of this size
BATCH_SIZE = 3


class SuspectGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load(
            "app/prompts/suspect/system.txt"
        )
        self.build_prompt = PromptLoader.load(
            "app/prompts/suspect/build.txt"
        )

    def generate(
        self,
        request: SuspectGenerationRequest,
        clearability_feedback: str = "",
    ) -> SuspectGenerationListSchema:
        """Generate suspects in batches for better cross-consistency and token efficiency.

        Instead of 6 sequential LLM calls (one per suspect), generates suspects
        in batches of BATCH_SIZE. This reduces:
        - Input token duplication (~4K request_data sent once per batch, not per suspect)
        - API round-trips (2 calls instead of 6 for 6 suspects)
        - Rate-limit sleeps (1 inter-batch sleep instead of 5 inter-suspect sleeps)

        Args:
            request: Suspect generation request with scenario context.
            clearability_feedback: If non-empty, feedback from a previous
                clearability failure to guide generation fixes.

        Returns:
            SuspectGenerationListSchema: All generated suspects.
        """
        suspect_count = request.generation_config.count
        culprit_ids = request.ground_truth.culprit_ids

        # Build assignment list: [(suspect_id, is_culprit), ...]
        assignments = [
            (i + 1, (i + 1) in culprit_ids)
            for i in range(suspect_count)
        ]

        # Split into batches
        batches = [
            assignments[i:i + BATCH_SIZE]
            for i in range(0, len(assignments), BATCH_SIZE)
        ]

        all_suspects: List[SuspectGenerationSchema] = []

        for batch_idx, batch in enumerate(batches):
            batch_ids = [a[0] for a in batch]
            logger.info(
                f"Generating suspect batch {batch_idx + 1}/{len(batches)} "
                f"(IDs: {batch_ids})..."
            )

            # Build lightweight summary of previously generated suspects
            existing_summary = [
                {
                    "suspect_id": s.suspect_id,
                    "name": s.name,
                    "role": s.role,
                    "is_culprit": s.is_culprit,
                }
                for s in all_suspects
            ]

            result = None
            for attempt in range(3):
                try:
                    result = self._generate_batch(
                        request=request,
                        batch=batch,
                        already_generated_summary=existing_summary,
                        clearability_feedback=clearability_feedback,
                    )
                    break
                except Exception as e:
                    logger.warning(
                        f"  Batch {batch_idx + 1} attempt {attempt + 1} failed: {e}"
                    )
                    time.sleep(2)

            if result is None:
                raise RuntimeError(
                    f"Failed to generate suspect batch {batch_idx + 1} (IDs: {batch_ids})"
                )

            # Validate batch output
            for suspect in result.suspects:
                logger.info(
                    f"  Suspect {suspect.suspect_id} ({suspect.name}) generated"
                )
            all_suspects.extend(result.suspects)

            # Rate-limit between batches (skip after last)
            if batch_idx < len(batches) - 1:
                time.sleep(3)

        return SuspectGenerationListSchema(suspects=all_suspects)

    def _generate_batch(
        self,
        request: SuspectGenerationRequest,
        batch: List[tuple],
        already_generated_summary: List[dict],
        clearability_feedback: str = "",
    ) -> SuspectGenerationListSchema:
        """Generate a batch of suspects in a single LLM call.

        Args:
            request: Original request with scenario context.
            batch: List of (suspect_id, is_culprit) tuples for this batch.
            already_generated_summary: Lightweight summaries of prior suspects.
            clearability_feedback: Optional feedback from clearability failure.

        Returns:
            SuspectGenerationListSchema: Generated suspects for this batch.
        """
        prompt = self._build_batch_prompt(
            request=request,
            batch=batch,
            already_generated_summary=already_generated_summary,
            clearability_feedback=clearability_feedback,
        )

        # Request list schema for multiple suspects
        raw = self.llm.complete(
            system=self.system_prompt,
            user=prompt,
            response_schema=SuspectGenerationListSchema.model_json_schema(),
        )

        json_text = extract_json(raw)
        data = safe_json_load(json_text)

        return SuspectGenerationListSchema.model_validate(data)

    def _build_batch_prompt(
        self,
        request: SuspectGenerationRequest,
        batch: List[tuple],
        already_generated_summary: List[dict],
        clearability_feedback: str = "",
    ) -> str:
        """Build prompt for a batch of suspects."""

        # Map skeleton info (if available)
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

        # Build batch assignment table
        batch_assignments = []
        for suspect_id, is_culprit in batch:
            batch_assignments.append(
                f"  - suspect_id: {suspect_id}, is_culprit: {is_culprit}"
            )
        assignments_text = "\n".join(batch_assignments)

        batch_instruction = f"""
{self.build_prompt}

[BATCH GENERATION]
You must generate EXACTLY {len(batch)} suspects in this batch:
{assignments_text}

[ALREADY GENERATED SUSPECTS]
{json.dumps(already_generated_summary, ensure_ascii=False, indent=2) if already_generated_summary else "None yet"}
{map_info}
[IMPORTANT]
- Do NOT duplicate names or roles from already generated suspects
- Do NOT duplicate names or roles between suspects in THIS batch
- Return a JSON object with a "suspects" array containing exactly {len(batch)} suspects
- Each suspect's suspect_id and is_culprit MUST match the assignments above
- Suspects within the same batch should have diverse personalities and roles
- Heard facts can reference suspect_ids from both this batch AND already generated suspects
"""

        # Inject clearability feedback if this is a retry
        if clearability_feedback:
            batch_instruction += f"""
[CLEARABILITY FIX — PREVIOUS ATTEMPT FAILED]
The previous generation failed clearability evaluation. The evaluator said:
{clearability_feedback}

You MUST address these issues:
- If secrets are too hard to unlock, lower thresholds or add more revealing timeline entries
- If the culprit cannot be distinguished, make their secrets and timeline gaps more telling
- If the deductive chain is too long, ensure critical clues are accessible early
- Ensure the culprit's hidden facts (threshold 50-90) form a clear logical chain when revealed
"""

        # Exclude map_skeleton from JSON dump to avoid duplication with map_info
        request_data = request.model_dump(mode='json', exclude={'map_skeleton'})

        return json.dumps({
            "input": request_data,
            "instruction": batch_instruction,
        }, ensure_ascii=False)

    def _build_single_prompt(
        self,
        request: SuspectGenerationRequest,
        suspect_id: int,
        is_culprit: bool,
        already_generated: List[SuspectGenerationSchema]
    ) -> str:
        """Legacy: single suspect generation prompt (kept for fallback)."""

        existing_summary = []
        for s in already_generated:
            existing_summary.append({
                "suspect_id": s.suspect_id,
                "name": s.name,
                "role": s.role,
                "is_culprit": s.is_culprit
            })

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

        request_data = request.model_dump(mode='json', exclude={'map_skeleton'})

        return json.dumps({
            "input": request_data,
            "instruction": single_instruction,
        }, ensure_ascii=False)
