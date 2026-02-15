# MaechuriAIServer Architecture

> 이 문서는 프로젝트의 전체 구조와 설계를 설명합니다.
> AI 어시스턴트가 코드베이스를 탐색하지 않고도 이해할 수 있도록 작성되었습니다.

---

## 1. 프로젝트 개요

**MaechuriAIServer**는 LLM 기반 미스터리 추리 게임 백엔드입니다.

- 시나리오 자동 생성 (LLM)
- 용의자 심문 (압박 시스템 + RAG)
- 증거 분석
- 추리 검증

---

## 2. 디렉토리 구조

```
app/
├── api/                          # FastAPI 라우트 및 의존성
│   ├── dependencies/             # 의존성 주입
│   │   ├── scenario_dependencies.py   # ScenarioService, SolveService
│   │   ├── chat_dependencies.py       # ChatService
│   │   └── __init__.py
│   ├── routes/                   # API 엔드포인트
│   │   ├── scenario.py           # /api/scenarios/*
│   │   ├── chat.py               # /api/chats/*
│   │   └── __init__.py
│   └── errors/
│
├── core/                         # 설정 및 유틸리티
│   ├── config.py                 # 환경변수 (Gemini API, PostgreSQL)
│   ├── json_retry.py             # JSON 파싱 재시도 로직
│   └── utils.py                  # extract_json, safe_json_load, format_history
│
├── db/                           # 데이터베이스 레이어
│   ├── database.py               # SQLAlchemy async 설정
│   ├── models/                   # ORM 모델
│   │   ├── scenario/
│   │   │   ├── main.py           # Scenario, Location
│   │   │   ├── suspect.py        # Suspect, SuspectTimeline, SuspectSecret
│   │   │   ├── clue.py           # Clue
│   │   │   └── world.py          # VisibilityRule, AccessRule, RequiredClue
│   │   ├── game_session.py       # GameSession (게임 상태)
│   │   └── embedding/
│   │       └── chat_embedding.py # ChatMessageEmbedding
│   └── repositories/             # Repository 패턴
│       ├── scenario_repository.py
│       └── game_session_repository.py
│
├── models/                       # Pydantic 스키마
│   ├── domain/                   # 런타임 도메인 모델
│   │   ├── suspect_state.py      # SuspectState (압박, 공개된 비밀)
│   │   ├── dialogue_state.py
│   │   └── fsm/interrogation.py  # 상태 머신
│   └── schemas/                  # API 요청/응답 모델
│       ├── chat/
│       │   ├── request.py        # SuspectChatRequest, ClueChatRequest
│       │   └── response.py       # SuspectChatResponse, ClueChatResponse
│       ├── scenario/
│       │   ├── main.py           # ScenarioResult
│       │   └── ...
│       ├── solve.py              # ScenarioSolveRequest/Response
│       ├── pressure.py           # PressureJudgeOutput
│       └── clue.py
│
├── services/                     # 비즈니스 로직
│   ├── agent/                    # LLM 에이전트
│   │   ├── scenario_generator.py # 시나리오 생성
│   │   ├── suspect_generator.py  # 용의자 생성
│   │   ├── clue_generator.py     # 단서 생성
│   │   ├── map_generator.py      # 맵 생성
│   │   ├── suspect_actor.py      # 용의자 응답 생성
│   │   ├── pressure_judge.py     # 압박 평가
│   │   ├── clue_agent.py         # 단서 분석
│   │   └── solve_validator.py    # 추리 검증
│   ├── llm/
│   │   ├── llm_client.py         # 추상 클래스
│   │   └── gemini_client.py      # Gemini 구현
│   ├── embedding/
│   │   ├── embedding_service.py  # 임베딩 API
│   │   └── bge_m3_model.py       # BGE-M3 모델
│   ├── rag/
│   │   ├── rag_service.py        # RAG 오케스트레이션
│   │   ├── retriever.py          # 벡터 검색
│   │   ├── indexer.py            # 임베딩 인덱싱
│   │   └── context_builder.py    # 컨텍스트 조합
│   ├── npc/
│   │   └── chat_service.py       # 채팅 오케스트레이션
│   ├── scenario/
│   │   ├── scenario_service.py   # 시나리오 생성/저장
│   │   └── solve_service.py      # 추리 검증
│   └── prompt/
│       └── prompt_loader.py      # 프롬프트 로딩
│
├── prompts/                      # 프롬프트 템플릿 (.txt)
│   ├── actor/system.txt
│   ├── judge/system.txt
│   ├── solve/system.txt
│   ├── scenario/case.txt, skeleton.txt, expansion.txt
│   ├── suspect/system.txt, build.txt
│   ├── clue/generation.txt, chat_system.txt
│   └── map/skeleton.txt, detail.txt
│
├── main.py                       # FastAPI 앱 팩토리
└── test/                         # 테스트
```

---

## 3. 핵심 컴포넌트

### 3.1 데이터베이스 모델 (ORM)

#### Scenario (루트 테이블)
```python
Scenario
├── meta: difficulty, theme, tone, language
├── incident: type, summary, time_range, location, primary_object
├── ground_truth: crime_time_range, crime_location, crime_method
├── constraints: no_supernatural, no_time_travel
│
├── locations (1:N)        → Location
├── suspects (1:N)         → Suspect
├── clues (1:N)            → Clue
├── visibility_rules (1:N) → VisibilityRule
├── access_rules (1:N)     → AccessRule
├── required_clues (1:N)   → RequiredClue
└── game_sessions (1:N)    → GameSession
```

#### Suspect
```python
Suspect (PK: scenario_id + suspect_id)
├── profile: name, role, age, gender, description
├── truth: is_culprit, motive
├── personality: speech_style, emotional_tendency, lying_pattern
├── alibi_summary
│
├── timeline (1:N) → SuspectTimeline
│   └── time_range, location_id, activity, can_prove, witness
│
└── secrets (1:N)  → SuspectSecret
    └── threshold (0-100), content, trigger_clue_ids
```

#### GameSession (게임 상태)
```python
GameSession (PK: session_id + scenario_id)
├── current_pressure: int (전체 압박)
├── suspect_pressures: dict  # {suspect_id: pressure}
├── clue_seen_ids: list
├── suspect_interactions: dict  # {suspect_id: count}
├── clue_interactions: dict     # {clue_id: count}
└── timestamps: created_at, last_activity_at, completed_at
```

#### ChatMessageEmbedding (대화 히스토리)
```python
ChatMessageEmbedding
├── scenario_id, session_id
├── suspect_id (nullable), clue_id (nullable)
├── role: 'user' | 'suspect' | 'detective'
├── content, embedding (pgvector)
└── created_at
```

---

### 3.2 서비스 레이어

#### LLM 에이전트

| 에이전트 | 역할 | 입력 | 출력 |
|---------|------|------|------|
| `ScenarioGenerator` | 시나리오 생성 | 테마 | case → skeleton → expansion |
| `SuspectGenerator` | 용의자 생성 | expansion, clues, map | SuspectList |
| `ClueGenerator` | 단서 생성 | expansion, map | ClueSet |
| `MapGenerator` | 맵 생성 | expansion | skeleton → detail |
| `SuspectActor` | 용의자 롤플레이 | 압박, 컨텍스트 | 대화 응답 |
| `PressureJudge` | 압박 평가 | 유저 메시지, 단서 | pressure_delta |
| `ClueAgent` | 단서 분석 | 단서, 질문 | 분석 응답 |
| `SolveValidator` | 추리 검증 | ground_truth, 유저 추리 | 점수/피드백 |

#### 서비스 오케스트레이션

```
ScenarioService
├── ScenarioGenerator (case → skeleton → expansion)
├── MapGenerator (skeleton → detail)
├── ClueGenerator
├── SuspectGenerator
├── ScenarioRepository.save_scenario()
└── RAGService.index_scenario()

ChatService
├── GameSessionRepository (상태 로드/저장)
├── ScenarioRepository (용의자/단서 정보)
├── RAGService (컨텍스트 검색)
├── PressureJudge (압박 평가)
├── SuspectActor / ClueAgent (응답 생성)
└── RAGIndexer (대화 인덱싱)

SolveService
├── ScenarioRepository (ground_truth 조회)
├── EmbeddingService (유사도 계산)
├── SolveValidator (LLM 검증)
└── 점수 계산 및 응답 생성
```

---

### 3.3 RAG 시스템

```
RAGService
├── index_scenario()    # 시나리오 전체 임베딩
├── index_chat_message() # 대화 메시지 임베딩
├── get_suspect_context() # 용의자 컨텍스트 검색
└── get_clue_context()    # 단서 컨텍스트 검색

RAGRetriever
├── retrieve_timelines()  # 관련 타임라인
├── retrieve_secrets()    # 압박 기준 비밀
├── retrieve_chat_history() # 관련 대화
└── retrieve_clues()      # 관련 단서

ContextBuilder
├── build_timeline_context()
├── build_secret_context()
├── build_chat_history_context()
└── build_full_interrogation_context()
```

---

## 4. API 엔드포인트

### Scenario API (`/api/scenarios`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/daily` | 시나리오 생성 (백그라운드) |
| GET | `/data/{scenario_id}` | 시나리오 조회 |
| POST | `/data/{scenario_id}/index` | RAG 인덱싱 |
| POST | `/solve` | 추리 검증 |
| GET | `/tasks` | 모든 태스크 조회 |
| GET | `/tasks/{key}` | 태스크 상태 조회 |

### Chat API (`/api/chats`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/suspect` | 용의자 대화 |
| POST | `/clue` | 단서 분석 |

---

## 5. 핵심 플로우

### 5.1 시나리오 생성

```
POST /api/scenarios/daily
    │
    ├─ ScenarioTaskInfo 등록
    ├─ BackgroundTask 시작
    │
    └─ ScenarioService.generate_and_save()
        ├─ generate_case() → 평서문
        ├─ generate_skeleton() → 구조
        ├─ generate_expansion() → 상세
        ├─ generate_map_skeleton()
        ├─ generate_clues()
        ├─ generate_suspects()
        ├─ generate_map_detail()
        │
        ├─ ScenarioRepository.save_scenario()
        └─ RAGService.index_scenario()
```

### 5.2 용의자 심문

```
POST /api/chats/suspect
    │
    ├─ GameSession 로드/생성
    ├─ Suspect 정보 로드
    │
    ├─ RAG 컨텍스트 검색
    │   ├─ 관련 타임라인
    │   ├─ 공개된 비밀
    │   └─ 최근 대화 히스토리
    │
    ├─ PressureJudge.evaluate()
    │   └─ pressure_delta 계산
    │
    ├─ GameSession 압박 업데이트
    │
    ├─ SuspectActor.generate_response()
    │   ├─ 압박 단계 결정 (CALM/NERVOUS/CORNERED/BREAKDOWN)
    │   ├─ 비밀 공개 여부 결정
    │   └─ 응답 생성
    │
    ├─ 대화 메시지 RAG 인덱싱
    └─ GameSession 저장
```

### 5.3 추리 검증

```
POST /api/scenarios/solve
    │
    ├─ 범인 ID 검증 (필수)
    │   └─ 틀리면 즉시 INCORRECT
    │
    ├─ Ground Truth 문장 생성
    │   └─ "범인: X. 동기: Y. 수법: Z. 시간: A. 장소: B."
    │
    ├─ 임베딩 유사도 계산 (BGE-M3)
    │   ├─ >= 0.7 → 정답 (LLM 호출 안함)
    │   └─ < 0.7 → LLM 검증
    │
    ├─ SolveValidator.validate() (필요시)
    │   └─ 5개 요소 각 20점 채점
    │
    └─ 최종 점수 계산
        ├─ 범인 점수 (40%)
        ├─ 추리 점수 (60%)
        └─ 상태: CORRECT/PARTIAL/INCORRECT
```

---

## 6. 설계 패턴

| 패턴 | 적용 위치 | 설명 |
|------|----------|------|
| **Repository** | `ScenarioRepository`, `GameSessionRepository` | DB 접근 추상화 |
| **Dependency Injection** | `get_scenario_service()`, `get_chat_service()` | FastAPI Depends |
| **Singleton** | `get_embedding_service()`, `get_rag_service()` | 비용이 큰 리소스 공유 |
| **Strategy** | `LLMClient` → `GeminiClient` | LLM 구현 교체 가능 |
| **Builder** | `ContextBuilder` | 프롬프트 컨텍스트 조립 |
| **State Machine** | `SuspectState` | 압박 단계 (CALM→BREAKDOWN) |
| **Chain of Responsibility** | Judge → Actor → RAG → DB | 심문 플로우 |

---

## 7. 주요 기술 스택

| 구분 | 기술 |
|------|------|
| **웹 프레임워크** | FastAPI (async) |
| **데이터베이스** | PostgreSQL + SQLAlchemy 2.0 (async) |
| **벡터 DB** | pgvector (PostgreSQL 확장) |
| **LLM** | Google Gemini 2.5 Flash |
| **임베딩** | BGE-M3 (1024차원, 다국어) |
| **검증** | Pydantic v2 |
| **비동기** | asyncio, asyncpg |

---

## 8. 설정값

### 환경변수 (`app/core/config.py`)
```python
GEMINI_API_KEY      # Google Gemini API 키
POSTGRES_HOST       # PostgreSQL 호스트
POSTGRES_PORT       # PostgreSQL 포트
POSTGRES_USER       # PostgreSQL 사용자
POSTGRES_PASSWORD   # PostgreSQL 비밀번호
POSTGRES_DB         # PostgreSQL 데이터베이스
```

### 하드코딩된 상수

| 위치 | 상수 | 값 | 설명 |
|------|------|-----|------|
| `solve_service.py` | `SIMILARITY_THRESHOLD` | 0.7 | 임베딩 유사도 임계값 |
| `solve_service.py` | `PASSING_SCORE` | 70 | 통과 점수 |
| `solve_service.py` | `CULPRIT_WEIGHT` | 0.4 | 범인 점수 가중치 |
| `solve_service.py` | `REASONING_WEIGHT` | 0.6 | 추리 점수 가중치 |
| `gemini_client.py` | `temperature` | 0.2 | LLM 온도 |
| `gemini_client.py` | `max_tokens` | 8192 | 최대 토큰 |
| `json_retry.py` | `max_attempts` | 3 | JSON 파싱 재시도 횟수 |

---

## 9. 주요 설계 결정

1. **압박은 용의자별로 관리**: `suspect_pressures` dict로 각 용의자 압박 독립 추적
2. **비밀은 계층형**: threshold + trigger_clue_ids로 단계적 정보 공개
3. **RAG는 시나리오별 격리**: scenario_id 필터로 시나리오 간 데이터 분리
4. **GameSession 지연 생성**: 첫 채팅 시 자동 생성
5. **유사도 우선 검증**: 임베딩 유사도 먼저 확인 후 LLM fallback (비용 절감)
6. **Location ID 매핑**: 부분 일치 + fallback으로 LLM 생성 오류 흡수
7. **복합 키 사용**: (scenario_id, location_id) 관계로 시나리오 간 데이터 혼합 방지

---

## 10. 파일 작성 시 참고사항

### 새로운 에이전트 추가
1. `app/prompts/{agent_name}/system.txt` 생성
2. `app/models/schemas/` 에 출력 스키마 추가
3. `app/services/agent/{agent_name}.py` 생성
4. `PromptLoader.load()` 로 프롬프트 로드
5. `llm.complete()` 로 LLM 호출

### 새로운 API 엔드포인트 추가
1. `app/models/schemas/` 에 요청/응답 스키마 추가
2. `app/services/` 에 비즈니스 로직 구현
3. `app/api/dependencies/` 에 DI 함수 추가
4. `app/api/routes/` 에 라우트 추가
5. `app/main.py` 에 라우터 등록 (필요시)

### 새로운 DB 모델 추가
1. `app/db/models/` 에 ORM 모델 추가
2. `app/db/models/__init__.py` 에 export 추가
3. `app/db/repositories/` 에 Repository 메서드 추가
4. Alembic 마이그레이션 생성

---

## 11. 테스트

```
app/test/
├── test_embedding.py      # 임베딩 서비스 테스트
├── test_scenario.py       # 시나리오 생성 테스트
├── test_rag.py            # RAG 시스템 테스트
├── test_map.py            # 맵 생성 테스트
├── test_suspect_agent.py  # 용의자 에이전트 테스트
└── chat_logs/, output/    # 테스트 출력
```

실행:
```bash
pytest app/test/
```
