from pydantic import BaseModel


class SuspectChatRequest(BaseModel):
    scenario_id: int
    suspect_id: int
    user_message: str
    history: dict = {}


class ClueChatRequest(BaseModel):
    scenario_id: int
    clue_id: int
    user_message: str
    history: dict = {}


class ChatResponse(BaseModel):
    user_message: str
    history: dict
    answer: str

