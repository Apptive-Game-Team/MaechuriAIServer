from typing import Any, Literal

from pydantic import BaseModel, Field


class SuspectAgentDecision(BaseModel):
    """Agent routing decision before the final in-character answer."""

    action: Literal["respond", "use_tool"] = Field(
        description="Either respond or use_tool."
    )
    tool_name: str | None = Field(
        default=None,
        description="Name of the tool to call when action is use_tool."
    )
    tool_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the selected tool."
    )
    pressure_delta: int = Field(
        ge=-30, le=50,
        description="압박 변화량 (-30 ~ +50)"
    )
    reasoning: str = Field(description="판단 이유 (한국어)")
    detected_strategy: str = Field(
        description="탐지된 유저 전략 (clue_presentation/logical_deduction/contradiction_trap/timeline_attack/witness_pressure/empty_threat/baseless_accusation/sympathy/random)"
    )
    is_critical_hit: bool = Field(
        default=False,
        description="치명적인 질문/증거인지 (핵심 증거, 결정적 모순 등)"
    )
    response: str = Field(
        default="",
        description="If action is respond, the in-character Korean response."
    )


class SuspectActorOutput(BaseModel):
    """Combined judge evaluation + actor response."""
    # Judge fields
    pressure_delta: int = Field(
        ge=-30, le=50,
        description="압박 변화량 (-30 ~ +50)"
    )
    reasoning: str = Field(description="판단 이유 (한국어)")
    detected_strategy: str = Field(
        description="탐지된 유저 전략 (clue_presentation/logical_deduction/contradiction_trap/timeline_attack/witness_pressure/empty_threat/baseless_accusation/sympathy/random)"
    )
    is_critical_hit: bool = Field(
        default=False,
        description="치명적인 질문/증거인지 (핵심 증거, 결정적 모순 등)"
    )
    # Actor field
    response: str = Field(description="용의자의 인캐릭터 롤플레이 응답 (한국어)")
