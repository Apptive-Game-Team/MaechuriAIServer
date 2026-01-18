from typing import Optional, List
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import async_session_factory
from app.db.models import (
    Scenario,
    Location,
    VisibilityRule,
    AccessRule,
    RequiredEvidence,
    Suspect,
    SuspectTimeline,
    SuspectSecret,
    Clue
)
from app.models.schemas.suspect import (
    SuspectSchema,
    TimelineEntrySchema,
    SecretTierSchema,
    PersonalitySchema
)
from app.models.schemas.clue import ClueItemSchema


class ScenarioRepository:
    """
    SQLAlchemy implementation for scenario-related data access.
    Manages its own session lifecycle for compatibility with existing services.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self._external_session = session

    @asynccontextmanager
    async def _get_session(self):
        """Get session - use external if provided, else create new"""
        if self._external_session:
            yield self._external_session
        else:
            async with async_session_factory() as session:
                yield session

    async def get_scenario_by_id(self, scenario_id: int) -> Optional[dict]:
        """
        Retrieves the full scenario data.
        """
        async with self._get_session() as session:
            stmt = (
                select(Scenario)
                .where(Scenario.scenario_id == scenario_id)
                .options(
                    selectinload(Scenario.locations),
                    selectinload(Scenario.visibility_rules),
                    selectinload(Scenario.access_rules),
                    selectinload(Scenario.required_evidences),
                    selectinload(Scenario.clues),
                    selectinload(Scenario.suspects)
                    .selectinload(Suspect.timeline),
                    selectinload(Scenario.suspects)
                    .selectinload(Suspect.secrets),
                )
            )

            result = await session.execute(stmt)
            scenario = result.scalar_one_or_none()

            if not scenario:
                return None

            return self._scenario_to_dict(scenario)

    def _scenario_to_dict(self, scenario: Scenario) -> dict:
        """Convert Scenario ORM object to dict"""
        locations = [loc.name for loc in scenario.locations]
        suspects = [self._to_suspect_schema(s).model_dump() for s in scenario.suspects]
        clues = [self._to_clue_schema(c).model_dump() for c in scenario.clues]

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
                "location": scenario.incident_location,
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
                "crime_location": scenario.crime_location
            },
            "world_detail": {
                "locations": locations,
                "time_granularity_minutes": 30,
                "visibility_rules": [
                    {
                        "from_location": r.from_location,
                        "can_see": r.can_see or [],
                        "cannot_see": r.cannot_see or [],
                        "evidence_type": r.evidence_type
                    }
                    for r in scenario.visibility_rules
                ],
                "access_rules": [
                    {"location": r.location, "requires": r.requires}
                    for r in scenario.access_rules
                ]
            },
            "ground_truth_detail": {
                "culprit_count": len([s for s in scenario.suspects if s.is_culprit]),
                "crime_time_range": {
                    "start": scenario.crime_time_start,
                    "end": scenario.crime_time_end
                },
                "crime_location": scenario.crime_location,
                "culprit_ids": [s.suspect_id for s in scenario.suspects if s.is_culprit],
                "method": scenario.crime_method,
                "required_evidence": [
                    {"type": e.type, "min_count": e.min_count}
                    for e in scenario.required_evidences
                ]
            },
            "constraints": {
                "no_supernatural": scenario.no_supernatural,
                "no_time_travel": scenario.no_time_travel
            },
            "clues": {
                "clues": clues
            },
            "suspects": suspects
        }


    async def get_suspect_info(
        self,
        scenario_id: int,
        suspect_id: int
    ) -> Optional[SuspectSchema]:
        """
        Retrieves specific suspect profile, alibi, and persona info.
        """
        async with self._get_session() as session:
            stmt = (
                select(Suspect)
                .where(Suspect.scenario_id == scenario_id)
                .where(Suspect.suspect_id == suspect_id)
                .options(
                    selectinload(Suspect.timeline),
                    selectinload(Suspect.secrets)
                )
            )

            result = await session.execute(stmt)
            suspect = result.scalar_one_or_none()

            if not suspect:
                return None

            return self._to_suspect_schema(suspect)

    async def get_clue_info(
        self,
        scenario_id: int,
        clue_id: int
    ) -> Optional[ClueItemSchema]:
        """
        Retrieves detailed information about a specific clue.
        """
        async with self._get_session() as session:
            stmt = (
                select(Clue)
                .where(Clue.scenario_id == scenario_id)
                .where(Clue.clue_id == clue_id)
            )

            result = await session.execute(stmt)
            clue = result.scalar_one_or_none()

            if not clue:
                return None

            return self._to_clue_schema(clue)

    async def get_all_clues(self, scenario_id: int) -> List[ClueItemSchema]:
        """Get all clues for a scenario"""
        async with self._get_session() as session:
            stmt = (
                select(Clue)
                .where(Clue.scenario_id == scenario_id)
                .order_by(Clue.clue_id)
            )
            result = await session.execute(stmt)
            clues = result.scalars().all()
            return [self._to_clue_schema(c) for c in clues]

    async def get_all_suspects(self, scenario_id: int) -> List[SuspectSchema]:
        """Get all suspects for a scenario"""
        async with self._get_session() as session:
            stmt = (
                select(Suspect)
                .where(Suspect.scenario_id == scenario_id)
                .options(
                    selectinload(Suspect.timeline),
                    selectinload(Suspect.secrets)
                )
                .order_by(Suspect.suspect_id)
            )
            result = await session.execute(stmt)
            suspects = result.scalars().all()
            return [self._to_suspect_schema(s) for s in suspects]

    def _to_suspect_schema(self, suspect: Suspect) -> SuspectSchema:
        """Convert Suspect ORM object to SuspectSchema"""
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
            timeline=[
                TimelineEntrySchema(
                    time=t.time_range,
                    location=t.location,
                    activity=t.activity,
                    can_prove=t.can_prove,
                    witness=t.witness
                )
                for t in sorted(suspect.timeline, key=lambda x: x.timeline_id)
            ],
            secrets=[
                SecretTierSchema(
                    threshold=s.threshold,
                    content=s.content,
                    trigger_evidence_ids=s.trigger_evidence_ids or []
                )
                for s in sorted(suspect.secrets, key=lambda x: x.threshold)
            ],
            personality=PersonalitySchema(
                speech_style=suspect.speech_style,
                emotional_tendency=suspect.emotional_tendency,
                lying_pattern=suspect.lying_pattern
            ),
            critical_evidence_ids=suspect.critical_evidence_ids or []
        )

    def _to_clue_schema(self, clue: Clue) -> ClueItemSchema:
        """Convert Clue ORM object to ClueItemSchema"""
        return ClueItemSchema(
            id=clue.clue_id,
            name=clue.name,
            found_at=clue.found_at,
            description=clue.description,
            related_suspect_ids=clue.related_suspect_ids or [],
            logic_explanation=clue.logic_explanation,
            decoded_answer=clue.decoded_answer,
            is_red_herring=clue.is_red_herring
        )
