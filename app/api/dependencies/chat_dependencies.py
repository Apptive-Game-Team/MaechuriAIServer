from typing import Annotated

from fastapi import Depends

from app.db.repositories.chat_repository import ChatRepository
from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.llm.gemini_client import GeminiClient
from app.services.npc.chat_service import ChatService
from app.services.agent.suspect_agent import SuspectAgent
from app.services.agent.clue_agent import ClueAgent


def get_gemini() -> GeminiClient:
    return GeminiClient()


def get_chat_repository() -> ChatRepository:
    return ChatRepository()


def get_scenario_repository() -> ScenarioRepository:
    return ScenarioRepository()


def get_suspect_agent(
        llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> SuspectAgent:
    return SuspectAgent(llm_client)


def get_clue_agent(
        llm_client: Annotated[GeminiClient, Depends(get_gemini)],
) -> ClueAgent:
    return ClueAgent(llm_client)


def get_chat_service(
    chat_repository: Annotated[ChatRepository, Depends(get_chat_repository)],
    scenario_repository: Annotated[ScenarioRepository, Depends(get_scenario_repository)],
    suspect_agent: Annotated[SuspectAgent, Depends(get_suspect_agent)],
    clue_agent: Annotated[ClueAgent, Depends(get_clue_agent)]
) -> ChatService:
    return ChatService(chat_repository=chat_repository,
                       scenario_repository=scenario_repository,
                       suspect_agent=suspect_agent,
                       clue_agent=clue_agent)
