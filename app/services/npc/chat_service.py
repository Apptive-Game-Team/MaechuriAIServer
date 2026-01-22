from typing import Optional, List
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.scenario_repository import ScenarioRepository
from app.db.repositories.game_session_repository import GameSessionRepository
from app.services.agent.pressure_judge import PressureJudge
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.clue_agent import ClueAgent
from app.services.rag import RAGService, get_rag_service
from app.models.domain.suspect_state import SuspectState
from app.models.schemas.suspect import SuspectSchema
from app.models.schemas.chat import (
    SuspectChatResponse,
    ClueChatResponse
)


logger = logging.getLogger(__name__)


class ChatService:
    """
    심문 대화를 관리하는 오케스트레이터 서비스.
    GameSession을 사용하여 상태를 관리하고 RAG를 활용하여 컨텍스트를 검색합니다.
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
        session_id: str,
        scenario_id: int,
        suspect_id: int,
        user_message: str,
        evidence_id: Optional[int] = None,
        db: AsyncSession = None
    ) -> SuspectChatResponse:
        """용의자와 대화 (Stateful with GameSession).

        Args:
            session_id: 게임 세션 ID (UUID)
            scenario_id: 시나리오 ID
            suspect_id: 용의자 ID
            user_message: 유저 메시지
            evidence_id: 제시할 증거 ID (있다면)
            db: 데이터베이스 세션 (필수)
        """
        if not db:
            raise ValueError("Database session is required for GameSession management")

        # 1. GameSession 로드 및 검증/생성
        session_repo = GameSessionRepository(db)
        game_session = await session_repo.get_session(session_id, scenario_id)

        if not game_session:
            # 세션이 없으면 생성 (Lazy Creation)
            game_session = await session_repo.create_session(session_id, scenario_id)

        # 2. 용의자 데이터 로드
        suspect = await self.scenario_repository.get_suspect_info(
            scenario_id=game_session.scenario_id,
            suspect_id=suspect_id
        )

        if not suspect:
            return SuspectChatResponse(
                user_message=user_message,
                answer="용의자를 찾을 수 없습니다.",
                pressure=game_session.current_pressure,
                pressure_delta=0
            )

        # 3. 상태 복원 (GameSession 기반)
        # Use suspect-specific pressure if available
        suspect_pressure = game_session.suspect_pressures.get(str(suspect_id), 0)

        state = SuspectState(
            suspect_id=suspect_id,
            current_pressure=suspect_pressure,
            evidence_seen_ids=list(game_session.evidence_seen_ids),
            chat_history=[]  # 최근 대화는 RAG에서 가져옴
        )

        # 4. 증거 처리 (있다면)
        evidence = None
        if evidence_id:
            evidence = await self._get_evidence(scenario_id, evidence_id)
            if evidence:
                state.add_evidence(evidence_id)
                await session_repo.add_evidence_seen(session_id, scenario_id, evidence_id)

        # 5. RAG 컨텍스트 검색
        rag_context = None
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
            logger.warning(f"RAG context retrieval failed: {e}")

        # 6. Judge: pressure 변화량 평가
        judge_result = self.judge.evaluate(
            user_message=user_message,
            suspect_summary=self._create_suspect_summary(suspect),
            current_pressure=state.current_pressure,
            conversation_context=self._format_recent_context(state.chat_history),
            evidence_presented=evidence,
            suspect_alibi=suspect.alibi_summary,
            suspect_timeline=self._format_timeline(suspect.timeline)
        )

        # 7. Pressure 업데이트
        new_pressure = state.update_pressure(judge_result.pressure_delta)
        await session_repo.update_suspect_pressure(session_id, scenario_id, suspect_id, new_pressure)

        # 8. Actor: 응답 생성 (RAG 컨텍스트 포함)
        response = self.actor.generate_response(
            suspect=suspect,
            state=state,
            user_message=user_message,
            evidence_presented=evidence,
            rag_context=rag_context
        )

        # 9. RAG용 메시지 임베딩 저장
        try:
            # 메시지 인덱스는 suspect_interactions 값을 사용
            suspect_interactions = game_session.suspect_interactions.get(str(suspect_id), 0)
            message_idx = suspect_interactions * 2  # user + suspect = 2 messages per interaction

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
        except Exception as e:
            logger.warning(f"Chat message indexing failed: {e}")

        # 10. GameSession 진행도 업데이트
        await session_repo.increment_suspect_interaction(session_id, scenario_id, suspect_id)
        await db.commit()

        return SuspectChatResponse(
            user_message=user_message,
            answer=response,
            pressure=new_pressure,
            pressure_delta=judge_result.pressure_delta
        )

    async def clue_chat(
        self,
        session_id: str,
        scenario_id: int,
        clue_id: int,
        user_message: str,
        db: AsyncSession = None
    ) -> ClueChatResponse:
        """증거와 대화 (Stateful with GameSession).

        Args:
            session_id: 게임 세션 ID (UUID)
            scenario_id: 시나리오 ID
            clue_id: 증거 ID
            user_message: 유저 메시지
            db: 데이터베이스 세션 (필수)
        """
        if not db:
            raise ValueError("Database session is required for GameSession management")

        # 1. GameSession 로드 및 검증/생성
        session_repo = GameSessionRepository(db)
        game_session = await session_repo.get_session(session_id, scenario_id)

        if not game_session:
            game_session = await session_repo.create_session(session_id, scenario_id)

        # 2. 단서 정보 로드
        clue = await self.scenario_repository.get_clue_info(
            scenario_id=scenario_id,
            clue_id=clue_id
        )

        if not clue:
            return ClueChatResponse(
                user_message=user_message,
                answer="해당 증거를 찾을 수 없습니다."
            )

        clue_info = clue.model_dump()

        # 3. RAG 컨텍스트 검색
        rag_context = None
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
            logger.warning(f"RAG context retrieval failed: {e}")

        # RAG 컨텍스트를 clue_info에 추가
        if rag_context:
            clue_info["rag_context"] = rag_context

        # 4. ClueAgent 응답 생성
        response_message = await self.clue_agent.chat_generate(
            clue_info,
            user_message,
            []  # 히스토리는 RAG에서 가져온 컨텍스트 사용
        )

        # 5. RAG용 메시지 임베딩 저장
        try:
            clue_interactions = game_session.clue_interactions.get(str(clue_id), 0)
            message_idx = clue_interactions * 2

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
        except Exception as e:
            logger.warning(f"Chat message indexing failed: {e}")

        # 6. GameSession 진행도 업데이트
        await session_repo.increment_clue_interaction(session_id, scenario_id, clue_id)
        await db.commit()

        return ClueChatResponse(
            user_message=user_message,
            answer=response_message
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
