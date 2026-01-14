from dataclasses import dataclass, field
from typing import List


@dataclass
class SuspectState:
    """용의자 런타임 상태 (세션별)"""
    suspect_id: int
    current_pressure: int = 0
    evidence_seen_ids: List[int] = field(default_factory=list)
    chat_history: List[dict] = field(default_factory=list)

    def update_pressure(self, delta: int) -> int:
        """
        압박 업데이트 (0-100 클램핑).

        Args:
            delta: 변화량 (+/-)

        Returns:
            업데이트된 pressure 값
        """
        self.current_pressure = max(0, min(100, self.current_pressure + delta))
        return self.current_pressure

    def add_evidence(self, evidence_id: int) -> bool:
        """
        증거 추가 (중복 방지).

        Returns:
            True if newly added, False if already seen
        """
        if evidence_id not in self.evidence_seen_ids:
            self.evidence_seen_ids.append(evidence_id)
            return True
        return False

    def get_pressure_tier(self) -> str:
        """
        현재 압박 단계 반환.

        Returns:
            CALM (0-29), NERVOUS (30-59), CORNERED (60-84), BREAKDOWN (85-100)
        """
        if self.current_pressure < 30:
            return "CALM"
        elif self.current_pressure < 60:
            return "NERVOUS"
        elif self.current_pressure < 85:
            return "CORNERED"
        else:
            return "BREAKDOWN"

    def add_message(self, role: str, content: str) -> None:
        """대화 히스토리에 메시지 추가"""
        self.chat_history.append({"role": role, "content": content})

    def get_recent_history(self, count: int = 10) -> List[dict]:
        """최근 대화 히스토리 반환"""
        return self.chat_history[-count:] if len(self.chat_history) > count else self.chat_history

    def to_dict(self) -> dict:
        """상태를 dict로 변환 (저장/전송용)"""
        return {
            "suspect_id": self.suspect_id,
            "current_pressure": self.current_pressure,
            "evidence_seen_ids": self.evidence_seen_ids,
            "chat_history": self.chat_history
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SuspectState":
        """dict에서 상태 복원"""
        return cls(
            suspect_id=data.get("suspect_id", 0),
            current_pressure=data.get("current_pressure", 0),
            evidence_seen_ids=data.get("evidence_seen_ids", []),
            chat_history=data.get("chat_history", [])
        )
