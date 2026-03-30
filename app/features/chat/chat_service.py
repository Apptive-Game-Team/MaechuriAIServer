from typing import Optional, TYPE_CHECKING
import asyncio
import logging

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.db.repositories.scenario_repository import ScenarioRepository
    from app.features.global_.rag import RAGService
from app.db.database import async_session_factory
from app.db.repositories.game_session_repository import GameSessionRepository
from app.features.global_.agent.pressure_judge import PressureJudge
from app.features.global_.agent.suspect_actor import SuspectActor
from app.features.global_.agent.clue_agent import ClueAgent
from app.features.global_.agent.detective_agent import DetectiveAgent
from app.features.global_.rag import get_rag_service
from app.features.chat.formatters import ChatFormatter
from app.utils import MessageParser
from app.models.domain.suspect_state import SuspectState
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
        rag_service: Optional["RAGService"] = None,
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
        db: AsyncSession,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> GeneralChatResponse:
        """형사와의 통합 대화

        사건에 대한 질문과 단서/용의자 관련 질문을 자연스럽게 처리합니다.
        [c:01], [s:01] 참조가 있으면 해당 정보를 RAG 컨텍스트에 포함합니다.

        Args:
            session_id: 게임 세션 ID (UUID)
            scenario_id: 시나리오 ID
            user_message: 유저 메시지
            db: 데이터베이스 세션 (필수)
            background_tasks: FastAPI BackgroundTasks for deferred work

        Returns:
            GeneralChatResponse: 형사의 응답
        """
        # 1. GameSession 로드 및 검증/생성
        session_repo = GameSessionRepository(db)
        game_session = await session_repo.get_session(session_id, scenario_id)

        if not game_session:
            game_session = await session_repo.create_session(session_id, scenario_id)

        # 2. user_message 파싱 [c:01] 또는 [s:01] 등의 정보 확인
        clue_ids, suspect_ids = MessageParser.parse_references(user_message)

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

        # 4. 참조된 단서 정보 로드 (병렬)
        clue_infos = []
        if clue_ids:
            clue_results = await asyncio.gather(
                *(self.scenario_repository.get_clue_info(scenario_id=scenario_id, clue_id=cid)
                  for cid in clue_ids)
            )
            clue_infos = [c.model_dump() for c in clue_results if c]

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

        # 6. RAG 인덱싱 + 세션 업데이트를 백그라운드로 이동
        general_interactions = game_session.suspect_interactions.get("general", 0)
        message_idx = general_interactions * 2

        if clue_infos:
            context_label = clue_infos[0].get("name", "형사")
            indexed_clue_id = clue_ids[0]
        else:
            context_label = "형사"
            indexed_clue_id = None

        if background_tasks:
            background_tasks.add_task(
                self._background_general_index,
                scenario_id=scenario_id,
                session_id=session_id,
                message_idx=message_idx,
                user_message=user_message,
                response=response,
                clue_id=indexed_clue_id,
                context_label=context_label,
                general_interactions=general_interactions,
            )
        else:
            # Fallback: inline indexing (e.g., in tests without BackgroundTasks)
            await self._inline_general_index(
                db=db,
                session_repo=session_repo,
                game_session=game_session,
                scenario_id=scenario_id,
                session_id=session_id,
                message_idx=message_idx,
                user_message=user_message,
                response=response,
                clue_id=indexed_clue_id,
                context_label=context_label,
                general_interactions=general_interactions,
            )

        # 7. 응답 반환
        return GeneralChatResponse(
            user_message=user_message,
            answer=response
        )

    async def suspect_chat(
        self,
        session_id: str,
        scenario_id: int,
        suspect_id: int,
        user_message: str,
        db: AsyncSession,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> SuspectChatResponse:
        """용의자와 대화 (Stateful with GameSession).

        메시지에서 [c:XX] 형식으로 단서를 참조할 수 있습니다.
        예: "이 증거에 대해 어떻게 생각해? [c:1]"

        Args:
            session_id: 게임 세션 ID (UUID)
            scenario_id: 시나리오 ID
            suspect_id: 용의자 ID
            user_message: 유저 메시지 ([c:ID]로 단서 참조 가능)
            db: 데이터베이스 세션 (필수)
            background_tasks: FastAPI BackgroundTasks for deferred work
        """
        # 1. GameSession + 용의자 데이터 + 시나리오 용의자 목록 병렬 로드
        session_repo = GameSessionRepository(db)

        game_session, suspect, suspect_names = await asyncio.gather(
            session_repo.get_session(session_id, scenario_id),
            self.scenario_repository.get_suspect_info(scenario_id, suspect_id),
            self.scenario_repository.get_suspect_names(scenario_id)
        )

        if not game_session:
            game_session = await session_repo.create_session(session_id, scenario_id)

        if not suspect:
            return SuspectChatResponse(
                user_message=user_message,
                answer="용의자를 찾을 수 없습니다.",
                pressure=game_session.current_pressure,
                pressure_delta=0,
                revealed_fact_ids=[]
            )

        # 2. user_message 파싱 [c:XX] 정보 확인
        clue_ids, _ = MessageParser.parse_references(user_message)

        # 3. 상태 복원 (GameSession 기반)
        suspect_pressure = game_session.suspect_pressures.get(str(suspect_id), 0)

        state = SuspectState(
            suspect_id=suspect_id,
            current_pressure=suspect_pressure,
            clue_seen_ids=list(game_session.clue_seen_ids),
        )

        # 4. 단서 처리 (메시지에서 파싱된 경우)
        clue = None
        if clue_ids:
            clue_id = clue_ids[0]  # 첫 번째 단서 사용
            clue = await self._get_clue(scenario_id, clue_id)
            if clue:
                state.add_clue(clue_id)
                await session_repo.add_clue_seen_on_session(game_session, clue_id)

        # 5. RAG 컨텍스트 검색
        rag_context = None
        rag_relevant_fact_ids = []
        try:
            rag_result = await self.rag_service.get_suspect_context(
                db=db,
                scenario_id=scenario_id,
                suspect_id=suspect_id,
                query=user_message,
                current_pressure=state.current_pressure,
                session_id=session_id,
                suspect_names=suspect_names,
            )
            if rag_result:
                if rag_result.full_context:
                    rag_context = rag_result.full_context
                rag_relevant_fact_ids = rag_result.retrieved_fact_ids
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")

        # 6. 단일 LLM 호출: Judge + Actor 통합
        responder_result = await self.actor.arespond(
            user_message=user_message,
            suspect=suspect,
            state=state,
            clue_presented=clue,
            knowledge_context=rag_context,
        )

        # 7. Pressure 업데이트
        new_pressure = state.update_pressure(responder_result.pressure_delta)
        await session_repo.update_suspect_pressure_on_session(game_session, suspect_id, new_pressure)
        await db.commit()
        response = responder_result.response

        # 8. RAG 인덱싱 + 상호작용 증가를 백그라운드로 이동
        suspect_interactions = game_session.suspect_interactions.get(str(suspect_id), 0)
        message_idx = suspect_interactions * 2

        if background_tasks:
            background_tasks.add_task(
                self._background_suspect_index,
                scenario_id=scenario_id,
                session_id=session_id,
                suspect_id=suspect_id,
                suspect_name=suspect.name,
                message_idx=message_idx,
                user_message=user_message,
                response=response,
            )
        else:
            await self._inline_suspect_index(
                db=db,
                session_repo=session_repo,
                game_session=game_session,
                scenario_id=scenario_id,
                session_id=session_id,
                suspect_id=suspect_id,
                suspect_name=suspect.name,
                message_idx=message_idx,
                user_message=user_message,
                response=response,
            )

        # 9. 현재 pressure로 공개된 fact ID 계산
        # get_all_accessible_facts() already filters by threshold <= pressure,
        # so every fact in rag_relevant_fact_ids is already unlocked.
        rag_relevant_fact_set = set(rag_relevant_fact_ids)
        revealed_fact_ids = [
            fact.fact_id for fact in suspect.facts
            if fact.fact_id in rag_relevant_fact_set
        ]

        return SuspectChatResponse(
            user_message=user_message,
            answer=response,
            pressure=new_pressure,
            pressure_delta=responder_result.pressure_delta,
            revealed_fact_ids=revealed_fact_ids
        )

    async def clue_chat(
        self,
        session_id: str,
        scenario_id: int,
        clue_id: int,
        user_message: str,
        db: AsyncSession,
        background_tasks: Optional[BackgroundTasks] = None
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
            background_tasks: FastAPI BackgroundTasks for deferred work
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

        # 5. RAG 인덱싱 + 세션 업데이트를 백그라운드로 이동
        clue_interactions = game_session.clue_interactions.get(str(clue_id), 0)
        message_idx = clue_interactions * 2

        if background_tasks:
            background_tasks.add_task(
                self._background_clue_index,
                scenario_id=scenario_id,
                session_id=session_id,
                clue_id=clue_id,
                clue_name=clue.name,
                message_idx=message_idx,
                user_message=user_message,
                response=response_message,
            )
        else:
            await self._inline_clue_index(
                db=db,
                session_repo=session_repo,
                game_session=game_session,
                scenario_id=scenario_id,
                session_id=session_id,
                clue_id=clue_id,
                clue_name=clue.name,
                message_idx=message_idx,
                user_message=user_message,
                response=response_message,
            )

        return ClueChatResponse(
            user_message=user_message,
            answer=response_message
        )

    # ── Background task functions (use their own DB session) ──

    async def _background_suspect_index(
        self,
        scenario_id: int,
        session_id: str,
        suspect_id: int,
        suspect_name: str,
        message_idx: int,
        user_message: str,
        response: str,
    ) -> None:
        """Background: index suspect chat messages + increment interaction."""
        try:
            async with async_session_factory() as db:
                # Batch index both messages in a single embedding forward pass
                await self.rag_service.index_chat_messages_batch(
                    db=db,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    messages=[
                        {"role": "user", "content": user_message, "message_index": message_idx},
                        {"role": "suspect", "content": response, "message_index": message_idx + 1},
                    ],
                    suspect_id=suspect_id,
                    context=suspect_name
                )
                # Increment interaction count
                session_repo = GameSessionRepository(db)
                await session_repo.increment_suspect_interaction(session_id, scenario_id, suspect_id)
                await db.commit()
        except Exception as e:
            logger.warning(f"Background suspect indexing failed: {e}")

    async def _background_general_index(
        self,
        scenario_id: int,
        session_id: str,
        message_idx: int,
        user_message: str,
        response: str,
        clue_id: Optional[int],
        context_label: str,
        general_interactions: int,
    ) -> None:
        """Background: index general chat messages + update interaction count."""
        try:
            async with async_session_factory() as db:
                await self.rag_service.index_chat_messages_batch(
                    db=db,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    messages=[
                        {"role": "user", "content": user_message, "message_index": message_idx},
                        {"role": "detective", "content": response, "message_index": message_idx + 1},
                    ],
                    clue_id=clue_id,
                    context=context_label
                )
                # Update general interaction count
                session_repo = GameSessionRepository(db)
                game_session = await session_repo.get_session(session_id, scenario_id)
                if game_session:
                    new_interactions = game_session.suspect_interactions.copy()
                    new_interactions["general"] = general_interactions + 1
                    game_session.suspect_interactions = new_interactions
                await db.commit()
        except Exception as e:
            logger.warning(f"Background general indexing failed: {e}")

    async def _background_clue_index(
        self,
        scenario_id: int,
        session_id: str,
        clue_id: int,
        clue_name: str,
        message_idx: int,
        user_message: str,
        response: str,
    ) -> None:
        """Background: index clue chat messages + increment interaction."""
        try:
            async with async_session_factory() as db:
                await self.rag_service.index_chat_messages_batch(
                    db=db,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    messages=[
                        {"role": "user", "content": user_message, "message_index": message_idx},
                        {"role": "detective", "content": response, "message_index": message_idx + 1},
                    ],
                    clue_id=clue_id,
                    context=clue_name
                )
                session_repo = GameSessionRepository(db)
                await session_repo.increment_clue_interaction(session_id, scenario_id, clue_id)
                await db.commit()
        except Exception as e:
            logger.warning(f"Background clue indexing failed: {e}")

    # ── Inline fallbacks (for tests / when no BackgroundTasks available) ──

    async def _inline_suspect_index(
        self,
        db: AsyncSession,
        session_repo: GameSessionRepository,
        game_session,
        scenario_id: int,
        session_id: str,
        suspect_id: int,
        suspect_name: str,
        message_idx: int,
        user_message: str,
        response: str,
    ) -> None:
        try:
            await self.rag_service.index_chat_messages_batch(
                db=db,
                scenario_id=scenario_id,
                session_id=session_id,
                messages=[
                    {"role": "user", "content": user_message, "message_index": message_idx},
                    {"role": "suspect", "content": response, "message_index": message_idx + 1},
                ],
                suspect_id=suspect_id,
                context=suspect_name
            )
        except Exception as e:
            logger.warning(f"Chat message indexing failed: {e}")
        await session_repo.increment_suspect_interaction_on_session(game_session, suspect_id)
        await db.commit()

    async def _inline_general_index(
        self,
        db: AsyncSession,
        session_repo: GameSessionRepository,
        game_session,
        scenario_id: int,
        session_id: str,
        message_idx: int,
        user_message: str,
        response: str,
        clue_id: Optional[int],
        context_label: str,
        general_interactions: int,
    ) -> None:
        try:
            await self.rag_service.index_chat_messages_batch(
                db=db,
                scenario_id=scenario_id,
                session_id=session_id,
                messages=[
                    {"role": "user", "content": user_message, "message_index": message_idx},
                    {"role": "detective", "content": response, "message_index": message_idx + 1},
                ],
                clue_id=clue_id,
                context=context_label
            )
        except Exception as e:
            logger.warning(f"Chat message indexing failed: {e}")
        new_interactions = game_session.suspect_interactions.copy()
        new_interactions["general"] = general_interactions + 1
        game_session.suspect_interactions = new_interactions
        await db.commit()

    async def _inline_clue_index(
        self,
        db: AsyncSession,
        session_repo: GameSessionRepository,
        game_session,
        scenario_id: int,
        session_id: str,
        clue_id: int,
        clue_name: str,
        message_idx: int,
        user_message: str,
        response: str,
    ) -> None:
        try:
            await self.rag_service.index_chat_messages_batch(
                db=db,
                scenario_id=scenario_id,
                session_id=session_id,
                messages=[
                    {"role": "user", "content": user_message, "message_index": message_idx},
                    {"role": "detective", "content": response, "message_index": message_idx + 1},
                ],
                clue_id=clue_id,
                context=clue_name
            )
        except Exception as e:
            logger.warning(f"Chat message indexing failed: {e}")
        await session_repo.increment_clue_interaction_on_session(game_session, clue_id)
        await db.commit()

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
