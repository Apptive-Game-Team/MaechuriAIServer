# Chat Service Latency Optimization

## Overview
Chat API 응답 지연 시간을 **~520-1560ms** 단축하고, event loop 블로킹 문제를 해결한 최적화입니다.

| Phase | 내용 | 절감 시간 |
|-------|------|-----------|
| 1 | Background Tasks로 후처리 이동 | 500-1500ms |
| 2 | DetectiveAgent 동기 LLM 호출 수정 | event loop 해방 |
| 3 | 불필요한 DB 재조회 제거 | 15-45ms |
| 4 | 독립 DB 쿼리 병렬화 | 5-15ms |
| 5 | Judge + Actor 단일 LLM 호출 통합 | 1000-3500ms |

---

## Phase 1: Background Tasks로 후처리 이동

**문제:** LLM 응답 생성 후 BGE-M3 임베딩 2회 + DB flush가 완료될 때까지 클라이언트가 대기함.

**해결:** RAG 인덱싱 + 상호작용 카운트 증가를 `BackgroundTasks`로 이동. 요청 스코프 DB 세션은 응답 후 닫히므로, 백그라운드에서 `async_session_factory()`로 별도 세션 생성.

**변경 파일:**
- `app/api/routes/chat.py` — 3개 라우트 핸들러에 `background_tasks: BackgroundTasks` 파라미터 추가
- `app/services/npc/chat_service.py` — `_background_*_index()` 메서드 3개 추가 (suspect, general, clue). `BackgroundTasks` 없을 때를 위한 `_inline_*_index()` 폴백 유지
- `app/services/rag/rag_service.py` — `index_chat_messages_batch()` 메서드 노출 (indexer 위임)
- `app/services/rag/indexer.py` — `index_chat_messages_batch`에서 `message_index`를 `msg.get("message_index", i)`로 수정

**추가 최적화:** 2회 순차 `index_chat_message()` 호출을 `index_chat_messages_batch()`로 교체하여 BGE-M3 forward pass 1회로 통합.

---

## Phase 2: DetectiveAgent 동기 LLM 호출 수정

**문제:** `DetectiveAgent.generate_response()`에서 `self.llm.complete()` (동기)를 호출하여 FastAPI event loop 전체가 블로킹됨. 동시 요청 처리 불가.

**해결:** `self.llm.complete()` → `await self.llm.acomplete()`

**변경 파일:**
- `app/services/agent/detective_agent.py` — 56행, 1줄 변경

---

## Phase 3: 불필요한 DB 재조회 제거

**문제:** `GameSessionRepository`의 `update_suspect_pressure()`, `add_clue_seen()`, `increment_suspect_interaction()` 등이 매번 `get_session()` SELECT를 실행. `chat_service.py`에서 이미 로드한 `game_session` 객체가 있음에도 재조회.

**해결:** `_on_session` 변형 메서드 추가 — 이미 로드된 `GameSession` 객체를 직접 받아 재조회 없이 처리.

**변경 파일:**
- `app/db/repositories/game_session_repository.py` — 4개 메서드 추가:
  - `update_suspect_pressure_on_session(game_session, suspect_id, new_pressure)`
  - `add_clue_seen_on_session(game_session, clue_id)`
  - `increment_suspect_interaction_on_session(game_session, suspect_id)`
  - `increment_clue_interaction_on_session(game_session, clue_id)`
- `app/services/npc/chat_service.py` — foreground 경로에서 `_on_session` 변형 사용

기존 메서드는 하위 호환성을 위해 유지.

---

## Phase 4: 독립 DB 쿼리 병렬화

**문제:** 서로 의존성 없는 DB 쿼리가 순차 실행됨.

**해결:** `asyncio.gather()`로 병렬 실행.

**변경 파일:**
- `app/services/npc/chat_service.py`:
  - `suspect_chat` — `get_session()` + `get_suspect_info()` 병렬 실행
  - `general_chat` — 단서 로딩 루프를 `asyncio.gather()` 병렬로 변경

---

## Phase 5: Judge + Actor를 단일 LLM 호출로 통합

**문제:** `suspect_chat`에서 Judge LLM 호출 후 Actor LLM 호출이 순차적으로 실행됨 (2회 LLM 왕복). Actor는 Judge의 `pressure_delta`만 필요하지만 별도 호출이 필수.

**해결:** `SuspectResponder` 에이전트를 신규 생성하여 Judge 평가 + Actor 응답을 단일 프롬프트로 통합. LLM이 pressure delta를 자체 계산 후 해당 tier에 맞는 롤플레이 응답을 생성.

```
Before: RAG + Judge (병렬) → Actor (순차) = 2회 LLM 호출
After:  RAG → SuspectResponder = 1회 LLM 호출
절감: ~1-3.5초 (LLM 왕복 1회 제거)
```

**변경 파일:**
- `app/models/schemas/suspect_responder.py` — `SuspectResponderOutput` 스키마 (judge 필드 + response)
- `app/prompts/suspect_responder/system.txt` — 통합 프롬프트 (judge 평가 → pressure 계산 → actor 응답)
- `app/services/agent/suspect_responder.py` — `SuspectResponder` 에이전트 (단일 `acomplete()` 호출)
- `app/services/npc/chat_service.py` — `suspect_chat`: 병렬 Judge + 순차 Actor → RAG → SuspectResponder로 교체
- `app/api/dependencies/chat_dependencies.py` — `get_suspect_responder` DI 팩토리 추가
- `app/services/npc/formatters/chat_formatter.py` — `build_suspect_prompt_data()` 공통 유틸리티 추출
- `app/services/agent/suspect_actor.py` — 공통 `build_suspect_prompt_data()` 사용으로 리팩토링

**참고:** `PressureJudge`, `SuspectActor`는 폴백/기타 용도를 위해 유지. API 응답 모델 (`SuspectChatResponse`) 변경 없음.

---

## 검증 방법

1. **기존 테스트:** `pytest app/test/` — 기존 테스트 통과 확인
2. **suspect_chat 수동 테스트:** 응답 즉시 반환 확인 후, `chat_message_embeddings` 테이블에 새 행 생성 확인
3. **general_chat 수동 테스트:** 동시 요청 시 event loop 블로킹 없음 확인
4. **로그 확인:** 백그라운드 작업 실패 시 warning 로그 출력 (응답에 영향 없음)
