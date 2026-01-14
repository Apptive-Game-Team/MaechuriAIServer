from typing import Optional
from pydantic import BaseModel, Field


class PressureJudgeOutput(BaseModel):
    """Judge LLM 출력"""
    pressure_delta: int = Field(
        ge=-30, le=50,
        description="압박 변화량 (-30 ~ +50)"
    )
    reasoning: str = Field(description="판단 이유 (한국어)")
    detected_strategy: str = Field(
        description="탐지된 유저 전략 (evidence_presentation/psychological_pressure/contradiction_trap/sympathy/timeline_attack/random)"
    )
    is_critical_hit: bool = Field(
        default=False,
        description="치명적인 질문/증거인지 (핵심 증거, 결정적 모순 등)"
    )
