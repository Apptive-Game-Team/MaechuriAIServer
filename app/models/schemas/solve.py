from pydantic import BaseModel


class ScenarioSolveRequest(BaseModel):
    scenario_id: int
    culprit_id: list[int]
    user_solution: str

class ScenarioSolveResponse(BaseModel):
    scenario_id: int
    success: bool