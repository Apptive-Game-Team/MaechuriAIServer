"""Mapper functions for converting between ORM models and schemas."""
from datetime import time
from typing import Dict, List, Optional

from app.db.models import Scenario, Suspect, Clue
from app.models.schemas.scenario import ScenarioResult
from app.models.schemas.suspect import (
    PersonalitySchema,
    FactSchema,
    SuspectSchema
)
from app.models.schemas.clue import ClueItemSchema


class ScenarioMapper:
    """Mapper class for scenario-related ORM to schema conversions."""

    @staticmethod
    def to_suspect_schema(suspect: Suspect) -> SuspectSchema:
        """Convert Suspect ORM object to SuspectSchema."""
        return SuspectSchema(
            suspect_id=suspect.suspect_id,
            name=suspect.name,
            role=suspect.role,
            age=suspect.age,
            gender=suspect.gender,
            description=suspect.description,
            is_culprit=suspect.is_culprit,
            motive=suspect.motive,
            alibi_summary=suspect.alibi_summary,
            facts=[
                FactSchema(
                    fact_id=fact.fact_id,
                    threshold=fact.threshold,
                    content=fact.content,
                    type=fact.type,
                )
                for fact in sorted(suspect.facts, key=lambda x: x.fact_id)
            ],
            personality=PersonalitySchema(
                speech_style=suspect.speech_style,
                emotional_tendency=suspect.emotional_tendency,
                lying_pattern=suspect.lying_pattern
            )
        )

    @staticmethod
    def to_clue_schema(clue: Clue, loc_map: Optional[Dict[int, str]] = None) -> ClueItemSchema:
        """Convert Clue ORM object to ClueItemSchema."""
        loc_map = loc_map or {}
        return ClueItemSchema(
            id=clue.clue_id,
            name=clue.name,
            found_at=loc_map.get(clue.location_id, f"Location_{clue.location_id}"),
            description=clue.description,
            related_suspect_ids=clue.related_suspect_ids or [],
            logic_explanation=clue.logic_explanation,
            decoded_answer=clue.decoded_answer,
            is_red_herring=clue.is_red_herring
        )

    @staticmethod
    def scenario_to_dict(scenario: Scenario) -> dict:
        """Convert Scenario ORM object to dict."""
        loc_map = {loc.location_id: loc.name for loc in scenario.locations}
        locations = [loc.name for loc in scenario.locations]
        suspects = [ScenarioMapper.to_suspect_schema(s).model_dump() for s in scenario.suspects]
        clues = [ScenarioMapper.to_clue_schema(c, loc_map).model_dump() for c in scenario.clues]

        return {
            "meta": {
                "difficulty": scenario.difficulty,
                "theme": scenario.theme,
                "tone": scenario.tone,
                "language": scenario.language
            },
            "incident": {
                "type": scenario.incident_type,
                "summary": scenario.incident_summary,
                "time_range": {
                    "start": scenario.incident_time_start,
                    "end": scenario.incident_time_end
                },
                "location": scenario.incident_loc.name if scenario.incident_loc else "Unknown",
                "primary_object": scenario.primary_object
            },
            "world": {
                "locations": locations,
                "time_granularity_minutes": 30
            },
            "ground_truth": {
                "culprit_count": len([s for s in scenario.suspects if s.is_culprit]),
                "crime_time_range": {
                    "start": scenario.crime_time_start,
                    "end": scenario.crime_time_end
                },
                "crime_location": scenario.crime_loc.name if scenario.crime_loc else "Unknown"
            },
            "world_detail": {
                "locations": locations,
                "time_granularity_minutes": 30,
                "visibility_rules": [
                    {
                        "from_location": loc.name,
                        "can_see": [loc_map.get(lid, "Unknown") for lid in loc.can_see] if loc.can_see else [],
                        "cannot_see": [loc_map.get(lid, "Unknown") for lid in loc.cannot_see] if loc.cannot_see else [],
                    }
                    for loc in scenario.locations
                    if loc.can_see or loc.cannot_see
                ],
                "access_rules": [
                    {"location": loc.name, "requires": loc.access_requires}
                    for loc in scenario.locations
                    if loc.access_requires
                ]
            },
            "ground_truth_detail": {
                "culprit_count": len([s for s in scenario.suspects if s.is_culprit]),
                "crime_time_range": {
                    "start": scenario.crime_time_start,
                    "end": scenario.crime_time_end
                },
                "crime_location": scenario.crime_loc.name if scenario.crime_loc else "Unknown",
                "culprit_ids": [s.suspect_id for s in scenario.suspects if s.is_culprit],
                "method": scenario.crime_method
            },
            "constraints": {
                "no_supernatural": scenario.no_supernatural,
                "no_time_travel": scenario.no_time_travel
            },
            "clues": clues,
            "suspects": suspects
        }

    @staticmethod
    def build_location_context(
        loc_name: str,
        loc_id: int,
        visibility_map: dict,
        access_map: dict,
        loc_map: dict
    ) -> str:
        """Location 정보를 자연어로 변환"""
        id_to_name = {v: k for k, v in loc_map.items()}

        vis_data = visibility_map.get(loc_name, {})
        can_see_ids = vis_data.get("can_see", [])
        cannot_see_ids = vis_data.get("cannot_see", [])

        can_see_names = [id_to_name.get(lid, f"장소{lid}") for lid in can_see_ids]
        cannot_see_names = [id_to_name.get(lid, f"장소{lid}") for lid in cannot_see_ids]

        access_req = access_map.get(loc_name)

        parts = [f"장소: {loc_name}"]

        if can_see_names:
            parts.append(f"이 장소에서 볼 수 있는 곳: {', '.join(can_see_names)}")
        if cannot_see_names:
            parts.append(f"이 장소에서 볼 수 없는 곳: {', '.join(cannot_see_names)}")
        if access_req:
            parts.append(f"접근 조건: {access_req}")

        return "\n".join(parts)

    @staticmethod
    def build_incident_context_from_result(scenario: ScenarioResult) -> str:
        """Incident 정보를 자연어로 변환 (ScenarioResult 버전)"""
        parts = [
            f"사건 유형: {scenario.incident.type}",
            f"발생 시간: {scenario.incident.time_range.start} ~ {scenario.incident.time_range.end}",
            f"발생 장소: {scenario.incident.location}",
            f"주요 대상: {scenario.incident.primary_object}",
            f"배경: {scenario.meta.theme} / {scenario.meta.tone}",
            f"사건 개요: {scenario.incident.summary}"
        ]
        return "\n".join(parts)

    @staticmethod
    def build_world_context_from_result(scenario: ScenarioResult) -> str:
        """World 정보를 자연어로 변환 (ScenarioResult 버전)"""
        locations = scenario.world_detail.locations or scenario.world.locations
        time_granularity = scenario.world.time_granularity_minutes

        parts = [
            f"배경 테마: {scenario.meta.theme}",
            f"분위기: {scenario.meta.tone}",
            f"난이도: {scenario.meta.difficulty}",
            f"시간 단위: {time_granularity}분",
            f"장소 목록: {', '.join(locations)}"
        ]
        return "\n".join(parts)
