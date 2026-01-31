from typing import Optional, List, TYPE_CHECKING, Tuple
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import deprecated

if TYPE_CHECKING:
    from app.db.repositories.scenario_repository import ScenarioRepository
    from app.services.rag import RAGService
from app.db.repositories.game_session_repository import GameSessionRepository
from app.services.agent.pressure_judge import PressureJudge
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.clue_agent import ClueAgent
from app.services.agent.detective_agent import DetectiveAgent
from app.services.rag import get_rag_service
from app.models.domain.suspect_state import SuspectState
from app.models.schemas.suspect import SuspectSchema
from app.models.schemas.chat import (
    SuspectChatResponse,
    ClueChatResponse,
    GeneralChatResponse
)


logger = logging.getLogger(__name__)


class ChatService:
    """
    심문 대화를 관리하는 오케스트레이터 서비스.
    GameSession을 사용하여 상태를 관리하고 RAG를 활용하여 컨텍스트를 검색합니다.
    """

    def __init__(
        self,
        scenario_repository: "ScenarioRepository",
        pressure_judge: PressureJudge,
        suspect_actor: SuspectActor,
        clue_agent: ClueAgent,
        detective_agent: Optional[DetectiveAgent] = None,
        rag_service: Optional["RAGService"] = None
    ):
        self.scenario_repository = scenario_repository
        self.judge = pressure_judge
        self.actor = suspect_actor
        self.clue_agent = clue_agent
        self.detective_agent = detective_agent
        self.rag_service = rag_service or get_rag_service()

    async def general_chat(
        self,
        session_id: str,
        scenario_id: int,
        user_message: str,
        db: AsyncSession
    ) -> GeneralChatResponse:
        """형사와의 통합 대화

        사건에 대한 질문과 단서/용의자 관련 질문을 자연스럽게 처리합니다.
        [c:01], [s:01] 참조가 있으면 해당 정보를 RAG 컨텍스트에 포함합니다.

        Args:
            session_id: 게임 세션 ID (UUID)
            scenario_id: 시나리오 ID
            user_message: 유저 메시지
            db: 데이터베이스 세션 (필수)

        Returns:
            GeneralChatResponse: 형사의 응답
        """
        # 1. GameSession 로드 및 검증/생성
        session_repo = GameSessionRepository(db)
        game_session = await session_repo.get_session(session_id, scenario_id)

        if not game_session:
            game_session = await session_repo.create_session(session_id, scenario_id)

        # 2. user_message 파싱 [c:01] 또는 [s:01] 등의 정보 확인
        clue_ids, suspect_ids = self._parse_message_references(user_message)

        # 3. RAG 컨텍스트 검색
        rag_context = ""
        history_context = ""

        try:
            rag_result = await self.rag_service.get_general_context(
                db=db,
                scenario_id=scenario_id,
                query=user_message,
                session_id=session_id,
                clue_ids=clue_ids if clue_ids else None,
                suspect_ids=suspect_ids if suspect_ids else None,
                top_k_context=5,
                top_k_clues=3,
                top_k_suspects=3,
                top_k_history=5,
                similarity_threshold=0.3
            )
            if rag_result.full_context:
                rag_context = rag_result.full_context
            if rag_result.relevant_history:
                history_context = rag_result.relevant_history
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")

        # 4. 참조된 단서 정보 로드 (있으면)
        clue_infos = []
        if clue_ids:
            for clue_id in clue_ids:
                clue = await self.scenario_repository.get_clue_info(
                    scenario_id=scenario_id,
                    clue_id=clue_id
                )
                if clue:
                    clue_infos.append(clue.model_dump())

        # 5. Detective Agent로 응답 생성
        if not self.detective_agent:
            return GeneralChatResponse(
                user_message=user_message,
                answer="형사 에이전트가 설정되지 않았습니다."
            )

        response = await self.detective_agent.generate_response(
            user_message=user_message,
            rag_context=rag_context,
            history_context=history_context,
            clue_infos=clue_infos if clue_infos else None
        )

        # 6. RAG용 메시지 임베딩 저장
        try:
            general_interactions = game_session.suspect_interactions.get("general", 0)
            message_idx = general_interactions * 2

            # 컨텍스트 라벨 결정 (단서 참조 시 첫 번째 단서 이름 사용)
            if clue_infos:
                context_label = clue_infos[0].get("name", "형사")
                indexed_clue_id = clue_ids[0]
            else:
                context_label = "형사"
                indexed_clue_id = None

            await self.rag_service.index_chat_message(
                db=db,
                scenario_id=scenario_id,
                session_id=session_id,
                message_index=message_idx,
                role="user",
                content=user_message,
                clue_id=indexed_clue_id,
                context=context_label
            )
            await self.rag_service.index_chat_message(
                db=db,
                scenario_id=scenario_id,
                session_id=session_id,
                message_index=message_idx + 1,
                role="detective",
                content=response,
                clue_id=indexed_clue_id,
                context=context_label
            )

            # general 상호작용 카운트 증가
            session_repo = GameSessionRepository(db)
            new_interactions = game_session.suspect_interactions.copy()
            new_interactions["general"] = general_interactions + 1
            game_session.suspect_interactions = new_interactions
            await db.commit()
        except Exception as e:
            logger.warning(f"Chat message indexing failed: {e}")

        # 7. 응답 반환
        return GeneralChatResponse(
            user_message=user_message,
            answer=response
        )

    def _parse_message_references(self, message: str) -> Tuple[List[int], List[int]]:
        """메시지에서 [c:01], [s:01] 등의 참조를 파싱합니다.

        Args:
            message: 유저 메시지

        Returns:
            Tuple[List[int], List[int]]: (clue_ids, suspect_ids)
        """
        clue_ids: List[int] = []
        suspect_ids: List[int] = []

        # [c:01], [c:1], [C:01] 등의 패턴 매칭
        clue_pattern = r'\[c:(\d+)\]'
        suspect_pattern = r'\[s:(\d+)\]'

        # 대소문자 무시
        clue_matches = re.findall(clue_pattern, message, re.IGNORECASE)
        suspect_matches = re.findall(suspect_pattern, message, re.IGNORECASE)

        # 문자열을 정수로 변환
        clue_ids = [int(m) for m in clue_matches]
        suspect_ids = [int(m) for m in suspect_matches]

        return clue_ids, suspect_ids

    async def suspect_chat(
        self,
        session_id: str,
        scenario_id: int,
        suspect_id: int,
        user_message: str,
        db: AsyncSession,
        clue_id: Optional[int] = None
    ) -> SuspectChatResponse:
        """용의자와 대화 (Stateful with GameSession).

        Args:
            session_id: 게임 세션 ID (UUID)
            scenario_id: 시나리오 ID
            suspect_id: 용의자 ID
            user_message: 유저 메시지
            db: 데이터베이스 세션 (필수)
            clue_id: 제시할 단서 ID (있다면)
        """
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
            clue_seen_ids=list(game_session.clue_seen_ids),
        )

        # 4. 단서 처리 (있다면)
        clue = None
        if clue_id:
            clue = await self._get_clue(scenario_id, clue_id)
            if clue:
                state.add_clue(clue_id)
                await session_repo.add_clue_seen(session_id, scenario_id, clue_id)

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
            clue_presented=clue,
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
            clue_presented=clue,
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
        db: AsyncSession
    ) -> ClueChatResponse:
        """단서와 대화 (Stateful with GameSession).

        .. deprecated::
            Use `general_chat` instead with `[c:{clue_id}]` reference in message.
            Clue analysis is now seamlessly integrated into general_chat.
            This method is kept for backwards compatibility.

        Args:
            session_id: 게임 세션 ID (UUID)
            scenario_id: 시나리오 ID
            clue_id: 단서 ID
            user_message: 유저 메시지
            db: 데이터베이스 세션 (필수)
        """
        import warnings
        warnings.warn(
            "clue_chat is deprecated. Use general_chat with [c:{clue_id}] reference instead.",
            DeprecationWarning,
            stacklevel=2
        )
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
                answer="해당 단서를 찾을 수 없습니다."
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

    async def _get_clue(self, scenario_id: int, clue_id: int) -> Optional[dict]:
        """단서 정보 조회"""
        clue = await self.scenario_repository.get_clue_info(scenario_id, clue_id)
        if clue:
            return {
                "id": clue.id,
                "name": clue.name,
                "description": clue.description
            }
        return None
