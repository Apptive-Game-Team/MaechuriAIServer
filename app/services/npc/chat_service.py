from typing import Optional

from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.agent.pressure_judge import PressureJudge
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.clue_agent import ClueAgent
from app.models.domain.suspect_state import SuspectState
from app.models.schemas.suspect import SuspectSchema


class ChatService:
    """
    심문 대화를 관리하는 오케스트레이터 서비스.

    흐름:
    1. PressureJudge가 유저 입력 평가 -> pressure 변화량 계산
    2. SuspectState 업데이트
    3. SuspectActor가 응답 생성
    """

    def __init__(
        self,
        scenario_repository: ScenarioRepository,
        pressure_judge: PressureJudge,
        suspect_actor: SuspectActor,
        clue_agent: ClueAgent
    ):
        self.scenario_repository = scenario_repository
        self.judge = pressure_judge
        self.actor = suspect_actor
        self.clue_agent = clue_agent

        # 세션별 상태 저장 (실제로는 Redis 등 사용 권장)
        self._states: dict[str, SuspectState] = {}

    async def suspect_chat(
        self,
        scenario_id: int,
        suspect_id: int,
        user_message: str,
        history: dict,
        evidence_id: Optional[int] = None
    ) -> dict:
        """
        용의자와 대화.

        Args:
            scenario_id: 시나리오 ID
            suspect_id: 용의자 ID
            user_message: 유저 메시지
            history: 이전 대화 히스토리 (클라이언트에서 전달)
            evidence_id: 제시할 증거 ID (있다면)

        Returns:
            {
                "answer": str,
                "pressure": int,
                "pressure_delta": int,
                "tier": str,
                "history": dict
            }
        """

        # 1. 용의자 데이터 로드
        suspect_data = await self.scenario_repository.get_suspect_info(
            scenario_id=scenario_id,
            suspect_id=suspect_id
        )

        if not suspect_data:
            return {
                "answer": "용의자를 찾을 수 없습니다.",
                "pressure": 0,
                "pressure_delta": 0,
                "tier": "UNKNOWN",
                "history": history
            }

        suspect = SuspectSchema.model_validate(suspect_data)

        # 2. 상태 로드 또는 생성
        state_key = f"{scenario_id}_{suspect_id}"
        state = self._get_or_create_state(state_key, suspect_id, history)

        # 3. 증거 처리 (있다면)
        evidence = None
        if evidence_id:
            evidence = await self._get_evidence(scenario_id, evidence_id)
            if evidence:
                state.add_evidence(evidence_id)

        # 4. Judge: pressure 변화량 평가 (alibi/timeline 정보 포함)
        judge_result = self.judge.evaluate(
            user_message=user_message,
            suspect_summary=self._create_suspect_summary(suspect),
            current_pressure=state.current_pressure,
            conversation_context=self._format_recent_context(state.chat_history),
            evidence_presented=evidence,
            suspect_alibi=suspect.alibi_summary,
            suspect_timeline=self._format_timeline(suspect.timeline)
        )

        # 5. Pressure 업데이트
        new_pressure = state.update_pressure(judge_result.pressure_delta)

        # 6. Actor: 응답 생성
        response = self.actor.generate_response(
            suspect=suspect,
            state=state,
            user_message=user_message,
            evidence_presented=evidence
        )

        # 7. 히스토리 업데이트
        state.add_message("user", user_message)
        state.add_message("suspect", response)

        # 8. 상태 저장
        self._states[state_key] = state

        return {
            "answer": response,
            "pressure": new_pressure,
            "pressure_delta": judge_result.pressure_delta,
            "tier": state.get_pressure_tier(),
            "history": {
                "chat_history": state.chat_history,
                "pressure": state.current_pressure,
                "evidence_seen_ids": state.evidence_seen_ids
            }
        }

    async def clue_chat(
        self,
        scenario_id: int,
        clue_id: int,
        user_message: str,
        history: dict
    ) -> str:
        """증거와 대화 (기존 로직 유지)"""
        clue_info = await self.scenario_repository.get_clue_info(
            scenario_id=scenario_id,
            clue_id=clue_id
        )

        if not clue_info:
            clue_info = {}

        response_message = await self.clue_agent.chat_generate(
            clue_info,
            user_message,
            history
        )

        return response_message

    def _get_or_create_state(
        self,
        state_key: str,
        suspect_id: int,
        history: dict
    ) -> SuspectState:
        """상태 로드 또는 새로 생성"""
        if state_key in self._states:
            return self._states[state_key]

        # 히스토리에서 상태 복원 시도
        return SuspectState(
            suspect_id=suspect_id,
            current_pressure=history.get("pressure", 0),
            evidence_seen_ids=history.get("evidence_seen_ids", []),
            chat_history=history.get("chat_history", [])
        )

    def _create_suspect_summary(self, suspect: SuspectSchema) -> str:
        """Judge용 용의자 요약"""
        culprit_str = "범인" if suspect.is_culprit else "무고한 용의자"
        return f"이름: {suspect.name}, 역할: {suspect.role}, 상태: {culprit_str}"

    def _format_timeline(self, timeline: list) -> str:
        """Judge용 타임라인 요약"""
        lines = []
        for t in timeline:
            prove_str = "증명가능" if t.can_prove else "미확인"
            lines.append(f"- {t.time}: {t.location}에서 {t.activity} ({prove_str})")
        return "\n".join(lines)

    def _format_recent_context(self, history: list, count: int = 5) -> str:
        """최근 대화 맥락"""
        recent = history[-count:] if len(history) > count else history
        if not recent:
            return "(대화 시작)"
        return "\n".join([f"{h['role']}: {h['content']}" for h in recent])

    async def _get_evidence(self, scenario_id: int, evidence_id: int) -> Optional[dict]:
        """증거 정보 조회"""
        clue = await self.scenario_repository.get_clue_info(scenario_id, evidence_id)
        if clue:
            return {
                "id": clue.get("id", evidence_id),
                "name": clue.get("name", "Unknown"),
                "description": clue.get("description", "")
            }
        return None
