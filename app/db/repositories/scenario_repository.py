from typing import Optional, List
from contextlib import asynccontextmanager
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import async_session_factory
from app.db.models import (
    Scenario,
    Location,
    VisibilityRule,
    AccessRule,
    RequiredClue,
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
                    selectinload(Scenario.incident_loc),
                    selectinload(Scenario.crime_loc),
                    selectinload(Scenario.visibility_rules),
                    selectinload(Scenario.access_rules),
                    selectinload(Scenario.required_clues),
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
        # Create ID -> Name map
        loc_map = {loc.location_id: loc.name for loc in scenario.locations}

        locations = [loc.name for loc in scenario.locations]
        suspects = [self._to_suspect_schema(s, loc_map).model_dump() for s in scenario.suspects]
        clues = [self._to_clue_schema(c, loc_map).model_dump() for c in scenario.clues]

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
                        "from_location": loc_map.get(r.from_location_id, "Unknown"),
                        "can_see": [loc_map.get(lid, "Unknown") for lid in r.can_see] if r.can_see else [],
                        "cannot_see": [loc_map.get(lid, "Unknown") for lid in r.cannot_see] if r.cannot_see else [],
                        "clue_type": r.clue_type
                    }
                    for r in scenario.visibility_rules
                ],
                "access_rules": [
                    {"location": loc_map.get(r.location_id, "Unknown"), "requires": r.requires}
                    for r in scenario.access_rules
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
                "method": scenario.crime_method,
                "required_clues": [
                    {"type": e.type, "min_count": e.min_count}
                    for e in scenario.required_clues
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
            # Need to fetch locations to map names
            loc_result = await session.execute(
                select(Location).where(Location.scenario_id == scenario_id)
            )
            loc_map = {loc.location_id: loc.name for loc in loc_result.scalars().all()}

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

            return self._to_suspect_schema(suspect, loc_map)

    async def get_clue_info(
        self,
        scenario_id: int,
        clue_id: int
    ) -> Optional[ClueItemSchema]:
        """
        Retrieves detailed information about a specific clue.
        """
        async with self._get_session() as session:
            # Need location map
            loc_result = await session.execute(
                select(Location).where(Location.scenario_id == scenario_id)
            )
            loc_map = {loc.location_id: loc.name for loc in loc_result.scalars().all()}

            stmt = (
                select(Clue)
                .where(Clue.scenario_id == scenario_id)
                .where(Clue.clue_id == clue_id)
            )

            result = await session.execute(stmt)
            clue = result.scalar_one_or_none()

            if not clue:
                return None

            return self._to_clue_schema(clue, loc_map)

    async def get_all_clues(self, scenario_id: int) -> List[ClueItemSchema]:
        """Get all clues for a scenario"""
        async with self._get_session() as session:
            loc_result = await session.execute(
                select(Location).where(Location.scenario_id == scenario_id)
            )
            loc_map = {loc.location_id: loc.name for loc in loc_result.scalars().all()}

            stmt = (
                select(Clue)
                .where(Clue.scenario_id == scenario_id)
                .order_by(Clue.clue_id)
            )
            result = await session.execute(stmt)
            clues = result.scalars().all()
            return [self._to_clue_schema(c, loc_map) for c in clues]

    async def get_all_suspects(self, scenario_id: int) -> List[SuspectSchema]:
        """Get all suspects for a scenario"""
        async with self._get_session() as session:
            loc_result = await session.execute(
                select(Location).where(Location.scenario_id == scenario_id)
            )
            loc_map = {loc.location_id: loc.name for loc in loc_result.scalars().all()}

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
            return [self._to_suspect_schema(s, loc_map) for s in suspects]

    def _to_suspect_schema(self, suspect: Suspect, loc_map: dict = None) -> SuspectSchema:
        """Convert Suspect ORM object to SuspectSchema"""
        loc_map = loc_map or {}
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
                    location=loc_map.get(t.location_id, f"Location_{t.location_id}"),
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
                    trigger_clue_ids=s.trigger_clue_ids or []
                )
                for s in sorted(suspect.secrets, key=lambda x: x.threshold)
            ],
            personality=PersonalitySchema(
                speech_style=suspect.speech_style,
                emotional_tendency=suspect.emotional_tendency,
                lying_pattern=suspect.lying_pattern
            ),
            critical_clue_ids=suspect.critical_clue_ids or []
        )

    def _to_clue_schema(self, clue: Clue, loc_map: dict = None) -> ClueItemSchema:
        """Convert Clue ORM object to ClueItemSchema"""
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

    async def save_scenario(self, scenario_data: dict) -> int:
        """
        Save a complete scenario to the database.

        Parameters
        ----------
        scenario_data : dict
            The scenario data from ScenarioResult.model_dump()

        Returns
        -------
        int
            The created scenario ID.
        """
        async with self._get_session() as session:
            # 1. Create main Scenario
            scenario = Scenario(
                # Meta
                difficulty=scenario_data["meta"]["difficulty"],
                theme=scenario_data["meta"]["theme"],
                tone=scenario_data["meta"]["tone"],
                language=scenario_data["meta"].get("language", "ko"),
                # Incident
                incident_type=scenario_data["incident"]["type"],
                incident_summary=scenario_data["incident"]["summary"],
                incident_time_start=self._parse_time(scenario_data["incident"]["time_range"]["start"]),
                incident_time_end=self._parse_time(scenario_data["incident"]["time_range"]["end"]),
                # incident_location has been replaced by incident_location_id (updated after creating locations)
                primary_object=scenario_data["incident"]["primary_object"],
                # Ground Truth
                crime_time_start=self._parse_time(scenario_data["ground_truth_detail"]["crime_time_range"]["start"]),
                crime_time_end=self._parse_time(scenario_data["ground_truth_detail"]["crime_time_range"]["end"]),
                # crime_location has been replaced by crime_location_id (updated after creating locations)
                crime_method=scenario_data["ground_truth_detail"].get("method", ""),
                # Constraints
                no_supernatural=scenario_data["constraints"].get("no_supernatural", True),
                no_time_travel=scenario_data["constraints"].get("no_time_travel", True),
            )
            session.add(scenario)
            await session.flush()  # Get scenario_id

            scenario_id = scenario.scenario_id

            # 2. Create Locations
            locations = scenario_data.get("world_detail", {}).get("locations", [])
            if not locations:
                locations = scenario_data.get("world", {}).get("locations", [])

            loc_map = {}  # name -> id mapping
            first_loc_id = None
            for idx, loc_name in enumerate(locations, start=1):
                location = Location(
                    scenario_id=scenario_id,
                    location_id=idx,
                    name=loc_name
                )
                session.add(location)
                loc_map[loc_name] = idx
                if first_loc_id is None:
                    first_loc_id = idx

            # Helper to map unknown locations to existing ones (Fuzzy Match & Fallback)
            def get_mapped_loc_id(name: str) -> int:
                # 1. Exact match
                if name in loc_map:
                    return loc_map[name]
                
                # 2. Partial match (e.g., "본관 도서관" matches "도서관")
                for existing_name, existing_id in loc_map.items():
                    if existing_name in name or name in existing_name:
                        return existing_id
                
                # 3. Fallback to first location
                return first_loc_id

            # Ensure locations are flushed to DB before referencing them in Scenario
            await session.flush()

            # Update Scenario with Location IDs
            incident_loc_name = scenario_data["incident"]["location"]
            crime_loc_name = scenario_data["ground_truth_detail"]["crime_location"]
            
            scenario.incident_location_id = get_mapped_loc_id(incident_loc_name)
            scenario.crime_location_id = get_mapped_loc_id(crime_loc_name)

            # 3. Create Visibility Rules
            visibility_rules = scenario_data.get("world_detail", {}).get("visibility_rules", [])
            for idx, rule in enumerate(visibility_rules, start=1):
                # Map names to IDs
                from_loc_id = get_mapped_loc_id(rule["from_location"])
                
                # Map lists of names to lists of IDs
                can_see_ids = [get_mapped_loc_id(name) for name in rule.get("can_see", [])]
                cannot_see_ids = [get_mapped_loc_id(name) for name in rule.get("cannot_see", [])]

                vis_rule = VisibilityRule(
                    scenario_id=scenario_id,
                    rule_id=idx,
                    from_location_id=from_loc_id,
                    can_see=can_see_ids,
                    cannot_see=cannot_see_ids,
                    clue_type=rule.get("clue_type")
                )
                session.add(vis_rule)

            # 4. Create Access Rules
            access_rules = scenario_data.get("world_detail", {}).get("access_rules") or []
            for idx, rule in enumerate(access_rules, start=1):
                loc_id = get_mapped_loc_id(rule["location"])
                
                acc_rule = AccessRule(
                    scenario_id=scenario_id,
                    rule_id=idx,
                    location_id=loc_id,
                    requires=rule["requires"]
                )
                session.add(acc_rule)

            # 5. Create Required Clues
            required_clues = scenario_data.get("ground_truth_detail", {}).get("required_clues", [])
            for idx, clue_info in enumerate(required_clues, start=1):
                req_clue = RequiredClue(
                    scenario_id=scenario_id,
                    clue_id=idx,
                    type=clue_info["type"],
                    min_count=clue_info["min_count"]
                )
                session.add(req_clue)

            # 6. Create Suspects with Timeline and Secrets
            suspects = scenario_data.get("suspects", [])
            culprit_ids = scenario_data.get("ground_truth_detail", {}).get("culprit_ids", [])

            for suspect_data in suspects:
                suspect_id = suspect_data["suspect_id"]
                is_culprit = suspect_id in culprit_ids or suspect_data.get("is_culprit", False)

                suspect = Suspect(
                    scenario_id=scenario_id,
                    suspect_id=suspect_id,
                    name=suspect_data["name"],
                    role=suspect_data["role"],
                    age=suspect_data["age"],
                    gender=suspect_data["gender"],
                    description=suspect_data["description"],
                    is_culprit=is_culprit,
                    motive=suspect_data.get("motive"),
                    alibi_summary=suspect_data["alibi_summary"],
                    # Personality
                    speech_style=suspect_data["personality"]["speech_style"],
                    emotional_tendency=suspect_data["personality"]["emotional_tendency"],
                    lying_pattern=suspect_data["personality"]["lying_pattern"],
                    critical_clue_ids=suspect_data.get("critical_clue_ids", [])
                )
                session.add(suspect)

                # Timeline
                for t_idx, timeline in enumerate(suspect_data.get("timeline", []), start=1):
                    loc_id = get_mapped_loc_id(timeline["location"])
                    
                    timeline_entry = SuspectTimeline(
                        scenario_id=scenario_id,
                        suspect_id=suspect_id,
                        timeline_id=t_idx,
                        time_range=timeline["time"],
                        location_id=loc_id,
                        activity=timeline["activity"],
                        can_prove=timeline["can_prove"],
                        witness=timeline.get("witness")
                    )
                    session.add(timeline_entry)

                # Secrets
                for s_idx, secret in enumerate(suspect_data.get("secrets", []), start=1):
                    secret_entry = SuspectSecret(
                        scenario_id=scenario_id,
                        suspect_id=suspect_id,
                        secret_id=s_idx,
                        threshold=secret["threshold"],
                        content=secret["content"],
                        trigger_clue_ids=secret.get("trigger_clue_ids", [])
                    )
                    session.add(secret_entry)

            # 7. Create Clues
            clues = scenario_data.get("clues", {}).get("clues", [])
            for clue_data in clues:
                found_at = clue_data["found_at"]
                loc_id = get_mapped_loc_id(found_at)
                
                clue = Clue(
                    scenario_id=scenario_id,
                    clue_id=clue_data["id"],
                    name=clue_data["name"],
                    location_id=loc_id,
                    description=clue_data["description"],
                    related_suspect_ids=clue_data.get("related_suspect_ids", []),
                    logic_explanation=clue_data["logic_explanation"],
                    decoded_answer=clue_data.get("decoded_answer"),
                    is_red_herring=clue_data.get("is_red_herring", False)
                )
                session.add(clue)

            await session.commit()
            return scenario_id

    def _parse_time(self, time_value) -> time:
        """Parse time value to datetime.time object."""
        if isinstance(time_value, time):
            return time_value
        if isinstance(time_value, str):
            try:
                # Remove 'Z' if present (UTC indicator)
                clean_time = time_value.replace("Z", "")
                
                # Handle "YYYY-MM-DDTHH:MM:SS" format if full datetime is provided
                if "T" in clean_time:
                    clean_time = clean_time.split("T")[1]
                
                # Handle "HH:MM:SS" or "HH:MM" format
                parts = clean_time.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                
                # Handle seconds with optional fractional part (e.g. "00.123")
                second_part = parts[2] if len(parts) > 2 else "0"
                second = int(float(second_part))
                
                return time(hour, minute, second)
            except Exception as e:
                # Log the error but re-raise ValueError for consistent handling
                raise ValueError(f"Failed to parse time string '{time_value}': {str(e)}")
                
        raise ValueError(f"Cannot parse time value: {time_value}")
