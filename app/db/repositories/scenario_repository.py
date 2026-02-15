from typing import Optional, List, Dict, Tuple
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import async_session_factory
from app.db.models import (
    Scenario,
    Location,
    Suspect,
    Fact,
    Clue,
    Map
)
from app.db.mappers import ScenarioMapper
from app.models.schemas.scenario import ScenarioResult
from app.core.map_position import calculate_map_positions
from app.models.schemas.suspect import SuspectSchema
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
                    selectinload(Scenario.clues),
                    selectinload(Scenario.suspects)
                    .selectinload(Suspect.facts),
                )
            )

            result = await session.execute(stmt)
            scenario = result.scalar_one_or_none()

            if not scenario:
                return None

            return ScenarioMapper.scenario_to_dict(scenario)

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
                    selectinload(Suspect.facts)
                )
            )

            result = await session.execute(stmt)
            suspect = result.scalar_one_or_none()

            if not suspect:
                return None

            return ScenarioMapper.to_suspect_schema(suspect)

    async def get_clue_info(
        self,
        scenario_id: int,
        clue_id: int
    ) -> Optional[ClueItemSchema]:
        """
        Retrieves detailed information about a specific clue.
        """
        async with self._get_session() as session:
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

            return ScenarioMapper.to_clue_schema(clue, loc_map)

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
            return [ScenarioMapper.to_clue_schema(c, loc_map) for c in clues]

    async def get_all_suspects(self, scenario_id: int) -> List[SuspectSchema]:
        """Get all suspects for a scenario"""
        async with self._get_session() as session:
            stmt = (
                select(Suspect)
                .where(Suspect.scenario_id == scenario_id)
                .options(
                    selectinload(Suspect.facts)
                )
                .order_by(Suspect.suspect_id)
            )
            result = await session.execute(stmt)
            suspects = result.scalars().all()
            return [ScenarioMapper.to_suspect_schema(s) for s in suspects]

    async def save_scenario(self, scenario_result: ScenarioResult) -> int:
        """
        Save a complete scenario to the database.

        Parameters
        ----------
        scenario_result : ScenarioResult
            The complete scenario result with clues, map, and suspects

        Returns
        -------
        int
            The created scenario ID.
        """
        async with self._get_session() as session:
            # 1. Create main Scenario
            scenario = Scenario(
                # Meta
                difficulty=scenario_result.meta.difficulty,
                theme=scenario_result.meta.theme,
                tone=scenario_result.meta.tone,
                language=scenario_result.meta.language,
                # Incident
                incident_type=scenario_result.incident.type,
                incident_summary=scenario_result.incident.summary,
                incident_time_start=scenario_result.incident.time_range.start,
                incident_time_end=scenario_result.incident.time_range.end,
                primary_object=scenario_result.incident.primary_object,
                # Ground Truth
                crime_time_start=scenario_result.ground_truth_detail.crime_time_range.start,
                crime_time_end=scenario_result.ground_truth_detail.crime_time_range.end,
                crime_method=scenario_result.ground_truth_detail.method,
                # Constraints
                no_supernatural=scenario_result.constraints.no_supernatural,
                no_time_travel=scenario_result.constraints.no_time_travel,
            )
            session.add(scenario)
            await session.flush()

            scenario_id = scenario.scenario_id

            # 2. Create Locations with visibility and access rules
            locations = scenario_result.world_detail.locations
            if not locations:
                locations = scenario_result.world.locations

            loc_map: Dict[str, int] = {}
            first_loc_id: Optional[int] = None
            for idx, loc_name in enumerate(locations, start=1):
                loc_map[loc_name] = idx
                if first_loc_id is None:
                    first_loc_id = idx

            def get_mapped_loc_id(name: str) -> int:
                """Map location name to ID with fuzzy matching and fallback."""
                if name in loc_map:
                    return loc_map[name]
                for existing_name, existing_id in loc_map.items():
                    if existing_name in name or name in existing_name:
                        return existing_id
                return first_loc_id or 1

            # Build visibility and access rule maps
            visibility_map: Dict[str, Dict[str, List[int]]] = {}
            for rule in scenario_result.world_detail.visibility_rules:
                can_see_ids = [get_mapped_loc_id(name) for name in rule.can_see]
                cannot_see_ids = [get_mapped_loc_id(name) for name in rule.cannot_see]
                visibility_map[rule.from_location] = {
                    "can_see": can_see_ids,
                    "cannot_see": cannot_see_ids
                }

            access_map: Dict[str, str] = {}
            if scenario_result.world_detail.access_rules:
                for rule in scenario_result.world_detail.access_rules:
                    access_map[rule.location] = rule.requires

            # Create Location objects
            for loc_name, loc_id in loc_map.items():
                vis_data = visibility_map.get(loc_name, {})
                location = Location(
                    scenario_id=scenario_id,
                    location_id=loc_id,
                    name=loc_name,
                    can_see=vis_data.get("can_see", []),
                    cannot_see=vis_data.get("cannot_see", []),
                    access_requires=access_map.get(loc_name)
                )
                session.add(location)

            await session.flush()

            # Update Scenario with Location IDs
            scenario.incident_location_id = get_mapped_loc_id(scenario_result.incident.location)
            scenario.crime_location_id = get_mapped_loc_id(scenario_result.ground_truth_detail.crime_location)

            # Build position maps from map data (if provided)
            suspect_positions: Dict[int, Tuple[int, int]] = {}
            clue_positions: Dict[int, Tuple[int, int]] = {}
            map_data = scenario_result.map

            if map_data:
                for obj in map_data.obj:
                    if obj.type == "suspect":
                        suspect_positions[obj.id] = (obj.position.x, obj.position.y)
                    elif obj.type == "clue":
                        clue_positions[obj.id] = (obj.position.x, obj.position.y)

            # 3. Create Suspects with Facts
            culprit_ids = scenario_result.ground_truth_detail.culprit_ids

            for suspect_schema in scenario_result.suspects:
                is_culprit = suspect_schema.suspect_id in culprit_ids or suspect_schema.is_culprit
                suspect_pos = suspect_positions.get(suspect_schema.suspect_id)

                suspect = Suspect(
                    scenario_id=scenario_id,
                    suspect_id=suspect_schema.suspect_id,
                    name=suspect_schema.name,
                    role=suspect_schema.role,
                    age=suspect_schema.age,
                    gender=suspect_schema.gender,
                    description=suspect_schema.description,
                    is_culprit=is_culprit,
                    motive=suspect_schema.motive,
                    alibi_summary=suspect_schema.alibi_summary,
                    speech_style=suspect_schema.personality.speech_style,
                    emotional_tendency=suspect_schema.personality.emotional_tendency,
                    lying_pattern=suspect_schema.personality.lying_pattern,
                    x=suspect_pos[0] if suspect_pos else None,
                    y=suspect_pos[1] if suspect_pos else None
                )
                session.add(suspect)

                for fact_schema in suspect_schema.facts:
                    fact_entry = Fact(
                        scenario_id=scenario_id,
                        suspect_id=suspect_schema.suspect_id,
                        fact_id=fact_schema.fact_id,
                        threshold=fact_schema.threshold,
                        content=fact_schema.content if isinstance(fact_schema.content, dict) else fact_schema.content.model_dump() if hasattr(fact_schema.content, 'model_dump') else fact_schema.content,
                        type=fact_schema.type,
                    )
                    session.add(fact_entry)

            # 4. Create Clues
            for clue_schema in scenario_result.clues:
                loc_id = get_mapped_loc_id(clue_schema.found_at)
                clue_pos = clue_positions.get(clue_schema.id)

                clue = Clue(
                    scenario_id=scenario_id,
                    clue_id=clue_schema.id,
                    name=clue_schema.name,
                    location_id=loc_id,
                    description=clue_schema.description,
                    related_suspect_ids=clue_schema.related_suspect_ids,
                    logic_explanation=clue_schema.logic_explanation,
                    decoded_answer=clue_schema.decoded_answer,
                    is_red_herring=clue_schema.is_red_herring,
                    x=clue_pos[0] if clue_pos else None,
                    y=clue_pos[1] if clue_pos else None
                )
                session.add(clue)

            # 5. Create context Facts (suspect_id=0)
            # Get the next fact_id after suspect facts
            max_suspect_fact_id = 0
            for suspect_schema in scenario_result.suspects:
                for fact_schema in suspect_schema.facts:
                    if fact_schema.fact_id > max_suspect_fact_id:
                        max_suspect_fact_id = fact_schema.fact_id
            context_fact_id = max_suspect_fact_id + 1

            # 5-1. Incident context
            incident_content = ScenarioMapper.build_incident_context_from_result(scenario_result)
            incident_fact = Fact(
                scenario_id=scenario_id,
                fact_id=context_fact_id,
                suspect_id=0,  # Context indicator
                threshold=0,
                type="incident",
                content={"text": incident_content, "extra_data": scenario_result.incident.model_dump(mode='json')}
            )
            session.add(incident_fact)
            context_fact_id += 1

            # 5-2. Location contexts
            for loc_name, loc_id in loc_map.items():
                loc_content = ScenarioMapper.build_location_context(
                    loc_name, loc_id, visibility_map, access_map, loc_map
                )
                loc_fact = Fact(
                    scenario_id=scenario_id,
                    fact_id=context_fact_id,
                    suspect_id=0,  # Context indicator
                    threshold=0,
                    type="location",
                    content={"text": loc_content, "extra_data": {"location_id": loc_id, "name": loc_name}}
                )
                session.add(loc_fact)
                context_fact_id += 1

            # 5-3. World context
            world_content = ScenarioMapper.build_world_context_from_result(scenario_result)
            world_fact = Fact(
                scenario_id=scenario_id,
                fact_id=context_fact_id,
                suspect_id=0,  # Context indicator
                threshold=0,
                type="world",
                content={"text": world_content, "extra_data": scenario_result.world.model_dump(mode='json')}
            )
            session.add(world_fact)

            # 6. Save Map elements (rooms, corridors)
            if map_data:
                map_result = calculate_map_positions(map_data)
                map_id_counter = 1
                for element in map_result.elements:
                    map_entry = Map(
                        scenario_id=scenario_id,
                        map_id=map_id_counter,
                        type=element.type,
                        name=element.name,
                        x=element.x,
                        y=element.y,
                        width=element.width,
                        height=element.height,
                        extra_data={**element.extra_data, "original_id": element.id}
                    )
                    session.add(map_entry)
                    map_id_counter += 1

            await session.commit()
            return scenario_id

    async def get_location_dict(self, scenario_id: int) -> Dict[int, str]:
        async with self._get_session() as session:
            loc_result = await session.execute(
                select(Location).where(Location.scenario_id == scenario_id)
            )
            locations = loc_result.scalars().all()
            return {loc.location_id: loc.name for loc in locations}
