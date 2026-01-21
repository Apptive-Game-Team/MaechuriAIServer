from typing import Optional, List
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.scenario_repository import ScenarioRepository
from app.services.agent.pressure_judge import PressureJudge
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.clue_agent import ClueAgent
from app.services.rag import RAGService, get_rag_service
from app.models.domain.suspect_state import SuspectState
from app.models.schemas.suspect import SuspectSchema
from app.models.schemas.chat import (
    ChatMessageSchema,
    SuspectChatHistorySchema,
    SuspectChatResponse,
    ClueChatHistorySchema,
    ClueChatResponse
)


class ChatService:
    """
    심문 대화를 관리하는 오케스트레이터 서비스.
    RAG를 활용하여 관련 컨텍스트를 검색하고 대화 품질을 향상시킵니다.
    """

    def __init__(
        self,
        scenario_repository: ScenarioRepository,
        pressure_judge: PressureJudge,
        suspect_actor: SuspectActor,
        clue_agent: ClueAgent,
        rag_service: Optional[RAGService] = None
    ):
        self.scenario_repository = scenario_repository
        self.judge = pressure_judge
        self.actor = suspect_actor
        self.clue_agent = clue_agent
        self.rag_service = rag_service or get_rag_service()

    async def suspect_chat(
        self,
        scenario_id: int,
        suspect_id: int,
        user_message: str,
        history: SuspectChatHistorySchema,
        evidence_id: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        session_id: Optional[str] = None
    ) -> SuspectChatResponse:
        """용의자와 대화.

        Args:
            scenario_id: 시나리오 ID
            suspect_id: 용의자 ID
            user_message: 유저 메시지
            history: 대화 히스토리
            evidence_id: 제시할 증거 ID (있다면)
            db: 데이터베이스 세션 (RAG 사용 시 필요)
            session_id: 세션 ID (RAG 히스토리 검색용)
        """

        # 1. 용의자 데이터 로드
        suspect = await self.scenario_repository.get_suspect_info(
            scenario_id=scenario_id,
            suspect_id=suspect_id
        )

        if not suspect:
            return SuspectChatResponse(
                user_message=user_message,
                answer="용의자를 찾을 수 없습니다.",
                pressure=history.pressure,
                pressure_delta=0,
                history=history
            )

        # 2. 상태 복원 (Stateless하게 요청받은 히스토리 기반으로 생성)
        state = self._restore_state(suspect_id, history)

        # 3. 증거 처리 (있다면)
        evidence = None
        if evidence_id:
            evidence = await self._get_evidence(scenario_id, evidence_id)
            if evidence:
                state.add_evidence(evidence_id)

        # 4. RAG 컨텍스트 검색 (db 세션이 있는 경우)
        rag_context = None
        if db is not None:
            try:
                rag_result = await self.rag_service.get_suspect_context(
                    db=db,
                    scenario_id=scenario_id,
                    suspect_id=suspect_id,
                    query=user_message,
                    current_pressure=state.current_pressure,
                    session_id=session_id,
                    top_k_timeline=3,
                    top_k_secrets=2,
                    top_k_history=5
                )
                if rag_result.full_context:
                    rag_context = rag_result.full_context
            except Exception as e:
                # RAG 실패 시 로그만 남기고 계속 진행
                import logging
                logging.getLogger(__name__).warning(f"RAG context retrieval failed: {e}")

        # 5. Judge: pressure 변화량 평가
        judge_result = self.judge.evaluate(
            user_message=user_message,
            suspect_summary=self._create_suspect_summary(suspect),
            current_pressure=state.current_pressure,
            conversation_context=self._format_recent_context(state.chat_history),
            evidence_presented=evidence,
            suspect_alibi=suspect.alibi_summary,
            suspect_timeline=self._format_timeline(suspect.timeline)
        )

        # 6. Pressure 업데이트
        new_pressure = state.update_pressure(judge_result.pressure_delta)

        # 7. Actor: 응답 생성 (RAG 컨텍스트 포함)
        response = self.actor.generate_response(
            suspect=suspect,
            state=state,
            user_message=user_message,
            evidence_presented=evidence,
            rag_context=rag_context
        )

        # 8. 히스토리 업데이트
        state.add_message("user", user_message)
        state.add_message("suspect", response)

        # 9. RAG용 메시지 임베딩 저장 (db 세션이 있고 session_id가 있는 경우)
        if db is not None and session_id:
            try:
                message_idx = len(state.chat_history) - 2  # user message index
                await self.rag_service.index_chat_message(
                    db=db,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    message_index=message_idx,
                    role="user",
                    content=user_message,
                    suspect_id=suspect_id,
                    context=suspect.name
                )
                await self.rag_service.index_chat_message(
                    db=db,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    message_index=message_idx + 1,
                    role="suspect",
                    content=response,
                    suspect_id=suspect_id,
                    context=suspect.name
                )
                await db.commit()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Chat message indexing failed: {e}")

        return SuspectChatResponse(
            user_message=user_message,
            answer=response,
            pressure=new_pressure,
            pressure_delta=judge_result.pressure_delta,
            history=SuspectChatHistorySchema(
                chat_history=[ChatMessageSchema(**msg) for msg in state.chat_history],
                pressure=state.current_pressure,
                evidence_seen_ids=state.evidence_seen_ids
            )
        )

    async def clue_chat(
        self,
        scenario_id: int,
        clue_id: int,
        user_message: str,
        history: ClueChatHistorySchema,
        db: Optional[AsyncSession] = None,
        session_id: Optional[str] = None
    ) -> ClueChatResponse:
        """증거와 대화.

        Args:
            scenario_id: 시나리오 ID
            clue_id: 증거 ID
            user_message: 유저 메시지
            history: 대화 히스토리
            db: 데이터베이스 세션 (RAG 사용 시 필요)
            session_id: 세션 ID (RAG 히스토리 검색용)
        """
        clue = await self.scenario_repository.get_clue_info(
            scenario_id=scenario_id,
            clue_id=clue_id
        )

        if not clue:
            return ClueChatResponse(
                user_message=user_message,
                answer="해당 증거를 찾을 수 없습니다.",
                history=history
            )

        clue_info = clue.model_dump()
        history_dict = [msg.model_dump() for msg in history.chat_history]

        # RAG 컨텍스트 검색 (db 세션이 있는 경우)
        rag_context = None
        if db is not None:
            try:
                rag_result = await self.rag_service.get_clue_context(
                    db=db,
                    scenario_id=scenario_id,
                    clue_id=clue_id,
                    query=user_message,
                    session_id=session_id,
                    top_k_clues=2,
                    top_k_history=5
                )
                if rag_result.full_context:
                    rag_context = rag_result.full_context
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"RAG context retrieval failed: {e}")

        # RAG 컨텍스트를 clue_info에 추가
        if rag_context:
            clue_info["rag_context"] = rag_context

        response_message = await self.clue_agent.chat_generate(
            clue_info,
            user_message,
            history_dict
        )

        # 히스토리 업데이트
        updated_history = ClueChatHistorySchema(
            chat_history=history.chat_history + [
                ChatMessageSchema(role="user", content=user_message),
                ChatMessageSchema(role="detective", content=response_message)
            ]
        )

        # RAG용 메시지 임베딩 저장 (db 세션이 있고 session_id가 있는 경우)
        if db is not None and session_id:
            try:
                message_idx = len(history.chat_history)
                await self.rag_service.index_chat_message(
                    db=db,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    message_index=message_idx,
                    role="user",
                    content=user_message,
                    clue_id=clue_id,
                    context=clue.name
                )
                await self.rag_service.index_chat_message(
                    db=db,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    message_index=message_idx + 1,
                    role="detective",
                    content=response_message,
                    clue_id=clue_id,
                    context=clue.name
                )
                await db.commit()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Chat message indexing failed: {e}")

        return ClueChatResponse(
            user_message=user_message,
            answer=response_message,
            history=updated_history
        )

    def _restore_state(
        self,
        suspect_id: int,
        history: SuspectChatHistorySchema
    ) -> SuspectState:
        """히스토리에서 상태 복원"""
        return SuspectState(
            suspect_id=suspect_id,
            current_pressure=history.pressure,
            evidence_seen_ids=list(history.evidence_seen_ids),
            chat_history=[msg.model_dump() for msg in history.chat_history]
        )

    def _create_suspect_summary(self, suspect: SuspectSchema) -> str:
        """Judge용 용의자 요약"""
        culprit_str = "범인" if suspect.is_culprit else "무고한 용의자"
        return f"이름: {suspect.name}, 역할: {suspect.role}, 상태: {culprit_str}"

    def _format_timeline(self, timeline: List) -> str:
        """Judge용 타임라인 요약"""
        lines = []
        for t in timeline:
            prove_str = "증명가능" if t.can_prove else "미확인"
            lines.append(f"- {t.time}: {t.location}에서 {t.activity} ({prove_str})")
        return "\n".join(lines)

    def _format_recent_context(self, history: List[dict], count: int = 5) -> str:
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
                "id": clue.id,
                "name": clue.name,
                "description": clue.description
            }
        return None

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
                "id": clue.id,
                "name": clue.name,
                "description": clue.description
            }
        return None
