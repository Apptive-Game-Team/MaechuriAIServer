from typing import Optional
from pydantic import BaseModel


class SuspectChatRequest(BaseModel):
    """용의자 대화 요청"""
    scenario_id: int
    suspect_id: int
    user_message: str
    history: dict = {}
    evidence_id: Optional[int] = None  # 증거 제시 시


class ClueChatRequest(BaseModel):
    """증거 대화 요청"""
    scenario_id: int
    clue_id: int
    user_message: str
    history: dict = {}


class SuspectChatResponse(BaseModel):
    """용의자 대화 응답"""
    user_message: str
    answer: str
    pressure: int
    pressure_delta: int
    tier: str  # CALM, NERVOUS, CORNERED, BREAKDOWN
    history: dict


class ChatResponse(BaseModel):
    """기본 대화 응답 (증거 대화용)"""
    user_message: str
    history: dict
    answer: str
