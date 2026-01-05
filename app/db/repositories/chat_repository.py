from typing import List, Dict, Any

class ChatRepository:
    """
    Interface for chat history and session data access.
    """

    async def get_chat_history(self,
                               user_id: int, 
                               scenario_id: int, 
                               target_id: int, 
                               target_type: str) -> List[Dict[str, str]]:
        pass

    async def get_clue_history(self,
                               user_id: int,
                               scenario_id: int,
                               clue_id: int) -> List[Dict[str, Any]]:
        pass

    async def save_message(self,
                           user_id: int, 
                           scenario_id: int, 
                           target_id: int, 
                           content: str) -> None:
        """
        Saves a new message to the chat history.
        role: 'user' or 'assistant'
        """
        pass

    async def save_clue_message(self,
                                user_id: int,
                                scenario_id: int,
                                clue_id: int,
                                content: str) -> None:
        pass

    async def clear_chat_history(self,
                                 user_id: int, 
                                 scenario_id: int) -> None:
        """
        Clears all chat history related to a specific scenario for a user.
        """
        pass
