from typing import List, Any

from pydantic import BaseModel

from app.models.schemas import ScenarioExpansion
from app.models.schemas.suspect.common import FactEntrySchema


class ClueGenerationRequest(BaseModel):
    """Request to generate suspects."""
    scenario_expansion: ScenarioExpansion
    facts: List[FactEntrySchema[Any]]

    @classmethod
    def from_expansion(
        cls,
        expansion: ScenarioExpansion,
        facts: List[FactEntrySchema[Any]],
    ) -> "ClueGenerationRequest":
        """Create request from ScenarioExpansion."""
        return cls(
            scenario_expansion=expansion,
            facts=facts,
        )
