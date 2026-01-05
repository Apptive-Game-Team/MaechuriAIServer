from typing import Dict, Any
from app.db.repositories.chat_repository import ChatRepository
from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.agent.suspect_agent import SuspectAgent
from app.services.agent.clue_agent import ClueAgent
from app.core.utils import format_history


class ChatService:
    def __init__(self, 
                 chat_repository: ChatRepository,
                 scenario_repository: ScenarioRepository,
                 suspect_agent: SuspectAgent,
                 clue_agent: ClueAgent):

        self.chat_repository = chat_repository
        self.scenario_repository = scenario_repository
        self.suspect_agent = suspect_agent
        self.clue_agent = clue_agent

    async def suspect_chat(self,
                           user_id: int,
                           scenario_id: int,
                           suspect_id: int,
                           user_message: str) -> Dict[str, Any]:
        """
        용의자와의 채팅 비즈니스 로직
        """
        # 1. 이전 대화 내역 조회
        previous_chat = await self.chat_repository.get_chat_history(
            user_id=user_id,
            scenario_id=scenario_id,
            target_id=suspect_id,
            target_type="suspect"
        )
        history_str = format_history(previous_chat)

        # 2. 성격 들고오기
        suspect_personality = await self.scenario_repository.get_suspect_info(
            scenario_id=scenario_id,
            suspect_id=suspect_id
        )
        if not suspect_personality:
            suspect_personality = {}

        # 3. response 만들기
        response_data = await self.suspect_agent.chat_generate(
            previous_chat=history_str,
            suspect_personality=suspect_personality,
            user_message=user_message
        )
        
        # 4. 결과 저장 및 반환
        # response_data는 {"response": "...", "emotion": "..."} 형태라고 가정
        response_text = response_data.get("response", "")
        
        await self.chat_repository.save_message(
            user_id=user_id,
            scenario_id=scenario_id,
            target_id=suspect_id,
            content=response_text
        )

        return response_data

    async def clue_chat(self,
                        user_id: int,
                        scenario_id: int,
                        clue_id: int,
                        user_message: str) -> Dict[str, Any]:
        """
        증거 분석/대화 비즈니스 로직
        """
        # 1. 이전 대화 내역 조회
        previous_chat = await self.chat_repository.get_clue_history(
            user_id=user_id,
            scenario_id=scenario_id,
            clue_id=clue_id
        )
        history_str = format_history(previous_chat)

        # 3. response 만들기
        # 경관은 성격 고정이라 판단하여 빈 dict 전달
        response_data = await self.suspect_agent.chat_generate(
            previous_chat=history_str,
            suspect_personality={}, 
            user_message=user_message
        )

        response_text = response_data.get("response", "")

        # 4. 결과 저장 (Clue 관련 저장이므로 save_clue_message 사용)
        await self.chat_repository.save_clue_message(
            user_id=user_id,
            scenario_id=scenario_id,
            clue_id=clue_id,
            content=response_text
        )

        return response_data
