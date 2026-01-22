"""Repository for managing game sessions."""
from typing import Optional
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GameSession


class GameSessionRepository:
    """Repository for game session data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        session_id: str,
        scenario_id: int
    ) -> GameSession:
        """
        Create a new game session.

        Parameters
        ----------
        session_id : str
            UUID string for the session
        scenario_id : int
            The scenario ID to play

        Returns
        -------
        GameSession
            The created game session
        """
        game_session = GameSession(
            session_id=session_id,
            scenario_id=scenario_id,
            current_pressure=0,
            suspect_pressures={},
            evidence_seen_ids=[],
            suspect_interactions={},
            clue_interactions={}
        )
        self.session.add(game_session)
        await self.session.flush()
        return game_session

    async def get_session(self, session_id: str, scenario_id: int) -> Optional[GameSession]:
        """
        Get game session by composite key.

        Parameters
        ----------
        session_id : str
            The session ID (user identifier)
        scenario_id : int
            The scenario ID

        Returns
        -------
        GameSession or None
            The game session if found
        """
        stmt = select(GameSession).where(
            GameSession.session_id == session_id,
            GameSession.scenario_id == scenario_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_pressure(self, session_id: str, scenario_id: int, new_pressure: int) -> None:
        """
        Update pressure level for a session.

        Parameters
        ----------
        session_id : str
            The session ID (user identifier)
        scenario_id : int
            The scenario ID
        new_pressure : int
            New pressure value (0-100)
        """
        stmt = (
            update(GameSession)
            .where(
                GameSession.session_id == session_id,
                GameSession.scenario_id == scenario_id
            )
            .values(
                current_pressure=new_pressure,
                last_activity_at=datetime.now()
            )
        )
        await self.session.execute(stmt)

    async def update_suspect_pressure(
        self,
        session_id: str,
        scenario_id: int,
        suspect_id: int,
        new_pressure: int
    ) -> None:
        """
        Update pressure level for a specific suspect.

        Parameters
        ----------
        session_id : str
            The session ID (user identifier)
        scenario_id : int
            The scenario ID
        suspect_id : int
            The suspect ID
        new_pressure : int
            New pressure value (0-100)
        """
        game_session = await self.get_session(session_id, scenario_id)
        if game_session:
            suspect_key = str(suspect_id)
            # Ensure we have a dict
            pressures = dict(game_session.suspect_pressures or {})
            pressures[suspect_key] = new_pressure

            # Explicitly re-assign to trigger SQLAlchemy change tracking for JSONB
            game_session.suspect_pressures = pressures

            # Update global pressure to max of all suspects
            if pressures:
                game_session.current_pressure = max(pressures.values())

            game_session.last_activity_at = datetime.now()
            await self.session.flush()

    async def add_evidence_seen(self, session_id: str, scenario_id: int, evidence_id: int) -> None:
        """
        Add evidence to seen list.

        Parameters
        ----------
        session_id : str
            The session ID (user identifier)
        scenario_id : int
            The scenario ID
        evidence_id : int
            The evidence ID shown to suspect
        """
        game_session = await self.get_session(session_id, scenario_id)
        if game_session and evidence_id not in game_session.evidence_seen_ids:
            game_session.evidence_seen_ids.append(evidence_id)
            game_session.last_activity_at = datetime.now()
            await self.session.flush()

    async def increment_suspect_interaction(
        self,
        session_id: str,
        scenario_id: int,
        suspect_id: int
    ) -> None:
        """
        Increment suspect interaction count.

        Parameters
        ----------
        session_id : str
            The session ID (user identifier)
        scenario_id : int
            The scenario ID
        suspect_id : int
            The suspect ID
        """
        game_session = await self.get_session(session_id, scenario_id)
        if game_session:
            suspect_key = str(suspect_id)
            interactions = game_session.suspect_interactions or {}
            interactions[suspect_key] = interactions.get(suspect_key, 0) + 1
            game_session.suspect_interactions = interactions
            game_session.last_activity_at = datetime.now()
            await self.session.flush()

    async def increment_clue_interaction(
        self,
        session_id: str,
        scenario_id: int,
        clue_id: int
    ) -> None:
        """
        Increment clue interaction count.

        Parameters
        ----------
        session_id : str
            The session ID (user identifier)
        scenario_id : int
            The scenario ID
        clue_id : int
            The clue ID
        """
        game_session = await self.get_session(session_id, scenario_id)
        if game_session:
            clue_key = str(clue_id)
            interactions = game_session.clue_interactions or {}
            interactions[clue_key] = interactions.get(clue_key, 0) + 1
            game_session.clue_interactions = interactions
            game_session.last_activity_at = datetime.now()
            await self.session.flush()

    async def complete_session(self, session_id: str, scenario_id: int) -> None:
        """
        Mark session as completed.

        Parameters
        ----------
        session_id : str
            The session ID (user identifier)
        scenario_id : int
            The scenario ID
        """
        stmt = (
            update(GameSession)
            .where(
                GameSession.session_id == session_id,
                GameSession.scenario_id == scenario_id
            )
            .values(
                completed_at=datetime.now(),
                last_activity_at=datetime.now()
            )
        )
        await self.session.execute(stmt)
