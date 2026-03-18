from typing import Annotated

from fastapi import Depends

from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.agent.detective_agent import DetectiveAgent
from app.services.llm.gemini_client import GeminiClient
from app.services.npc.chat_service import ChatService
from app.services.agent.pressure_judge import PressureJudge
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.suspect_responder import SuspectResponder
from app.services.agent.clue_agent import ClueAgent


def get_gemini() -> GeminiClient:
    return GeminiClient()


def get_scenario_repository() -> ScenarioRepository:
    return ScenarioRepository()


def get_pressure_judge(
    llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> PressureJudge:
    return PressureJudge(llm_client)


def get_suspect_actor(
    llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> SuspectActor:
    return SuspectActor(llm_client)


def get_clue_agent(
    llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> ClueAgent:
    return ClueAgent(llm_client)

def get_detective_agent(
    llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> DetectiveAgent:
    return DetectiveAgent(llm_client)


def get_suspect_responder(
    llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> SuspectResponder:
    return SuspectResponder(llm_client)


def get_chat_service(
    scenario_repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
    pressure_judge: Annotated[PressureJudge, Depends(get_pressure_judge)],
    suspect_actor: Annotated[SuspectActor, Depends(get_suspect_actor)],
    clue_agent: Annotated[ClueAgent, Depends(get_clue_agent)],
    detective_agent: Annotated[DetectiveAgent, Depends(get_detective_agent)],
    suspect_responder: Annotated[SuspectResponder, Depends(get_suspect_responder)]
) -> ChatService:
    return ChatService(
        scenario_repository=scenario_repository,
        pressure_judge=pressure_judge,
        suspect_actor=suspect_actor,
        clue_agent=clue_agent,
        detective_agent=detective_agent,
        suspect_responder=suspect_responder,
    )
