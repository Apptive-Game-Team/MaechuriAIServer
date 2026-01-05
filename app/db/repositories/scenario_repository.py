from abc import ABC, abstractmethod
from typing import Optional, List
from app.models.schemas.scenario import ScenarioResult
from app.models.schemas.clue import ClueItemSchema

class ScenarioRepository:
    """
    Interface for scenario-related data access.
    """
    
    async def get_scenario_by_id(self,
                                 scenario_id: int) -> Optional[ScenarioResult]:
        """
        Retrieves the full scenario data including skeleton, expansion, and clues.
        """
        pass

    async def get_suspect_info(self,
                               scenario_id: int,
                               suspect_id: int) -> Optional[dict]:
        """
        Retrieves specific suspect profile, alibi, and persona info.
        """
        pass

    async def get_clue_info(self,
                            scenario_id: int,
                            clue_id: int) -> Optional[ClueItemSchema]:
        """
        Retrieves detailed information about a specific clue.
        """
        pass

    async def save_scenario(self,
                            scenario: ScenarioResult) -> int:
        """
        Saves a generated scenario and returns its unique ID.
        """
        pass
