
from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.agent.suspect_agent import SuspectAgent
from app.services.agent.clue_agent import ClueAgent


class ChatService:
    def __init__(self,
                 scenario_repository: ScenarioRepository,
                 suspect_agent: SuspectAgent,
                 clue_agent: ClueAgent):
        self.scenario_repository = scenario_repository
        self.suspect_agent = suspect_agent
        self.clue_agent = clue_agent

    async def suspect_chat(self,
                           scenario_id: int,
                           suspect_id: int,
                           user_message: str,
                           history: dict) -> str:
        # 1. 성격 들고오기
        suspect_personality = await self.scenario_repository.get_suspect_info(
            scenario_id=scenario_id,
            suspect_id=suspect_id
        )

        if not suspect_personality:
            suspect_personality = {}

        # 2. history와 성격 기반으로 대화 생성
        response_message = await self.suspect_agent.chat_generate(
            suspect_personality,
            user_message,
            history)

        return response_message

    async def clue_chat(self,
                        scenario_id: int,
                        clue_id: int,
                        user_message: str,
                        history: dict) -> str:
        # 1. clue 정보 들고오기
        clue_info = await self.scenario_repository.get_clue_info(
            scenario_id=scenario_id,
            clue_id=clue_id
        )
        
        if not clue_info:
            clue_info = {}

        # 2. response_message 생성
        response_message = await self.clue_agent.chat_generate(
            clue_info,
            user_message,
            history
        )

        return response_message