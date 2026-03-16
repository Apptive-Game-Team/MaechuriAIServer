# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MaechuriAIServer is an LLM-powered mystery detective game backend (Korean-language focused). It handles scenario generation, suspect interrogation with a pressure system, evidence analysis, and deduction verification.

## Commands

### Run the server
```bash
uvicorn app.main:app --reload
```

### Run tests
```bash
# All tests
pytest app/test/

# Single test file
pytest app/test/test_embedding.py

# Single test
pytest app/test/test_embedding.py::test_function_name -v
```

### Docker
```bash
docker-compose up        # Starts app + Redis
docker-compose up --build  # Rebuild and start
```

### Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Tech Stack
- **Framework**: FastAPI (async) with Pydantic v2
- **Database**: PostgreSQL + SQLAlchemy 2.0 (async) + pgvector for embeddings
- **LLM**: Google Gemini (via `google-genai` SDK), configured in `app/services/llm/gemini_client.py`
- **Embedding**: BGE-M3 (1024-dim, multilingual) via sentence-transformers
- **Cache/State**: Redis for task status tracking
- **Python**: 3.12

### Key Layers

**API Layer** (`app/api/`): FastAPI routes with dependency injection.
- Routes: `scenario.py` (`/api/scenarios/*`), `chat.py` (`/api/chats/*`)
- Dependencies: Factory functions in `app/api/dependencies/` wire services together via `Depends()`

**Service Layer** (`app/services/`): Business logic, organized by domain.
- `agent/` — LLM-powered agents. Each agent has a corresponding prompt template in `app/prompts/`:
  - `ScenarioGenerator`: multi-step generation (case → skeleton → expansion)
  - `MapGenerator`: skeleton → detail
  - `ClueGenerator`, `SuspectGenerator`: generate game content from expansion
  - `SuspectActor`: roleplay responses during interrogation
  - `PressureJudge`: evaluates pressure delta from user messages
  - `SolveValidator`: scores player deductions against ground truth
- `llm/` — Abstract `LLMClient` with `GeminiClient` implementation
- `embedding/` — BGE-M3 model loading (singleton via `get_embedding_model()`)
- `rag/` — RAG pipeline: `RAGService` orchestrates `RAGRetriever`, `RAGIndexer`, `ContextBuilder`
- `npc/` — `ChatService` orchestrates suspect/clue chat flows
- `scenario/` — `ScenarioService` (generation + DB save), `SolveService` (deduction scoring), `ScenarioStateManager` (intermediate state to disk)
- `task/` — Redis-backed task status tracking for background scenario generation

**Database Layer** (`app/db/`):
- ORM models in `app/db/models/` — `Scenario` is root entity with 1:N relations to `Location`, `Suspect`, `Clue`, world rules
- `GameSession` tracks per-session state (pressure, seen clues, interaction counts)
- `ChatMessageEmbedding` stores conversation history with pgvector embeddings
- Repository pattern: `ScenarioRepository`, `GameSessionRepository`

**Prompts** (`app/prompts/`): `.txt` template files organized by agent (actor, judge, solve, scenario, suspect, clue, map). Loaded by `PromptLoader.load()`.

**Schemas** (`app/models/schemas/`): Pydantic request/response models. `app/models/domain/` has runtime state models (e.g., `SuspectState` with pressure stages CALM→NERVOUS→CORNERED→BREAKDOWN).

### Core Flows

1. **Scenario Generation** (`POST /api/scenarios/daily`): Runs as BackgroundTask. Pipeline: case → skeleton → expansion → map → clues → suspects → DB save → RAG index. Intermediate results saved to disk via `ScenarioStateManager`.

2. **Suspect Chat** (`POST /api/chats/suspect`): Load GameSession → RAG context retrieval → PressureJudge evaluates → update pressure → SuspectActor generates response → index chat message → save session.

3. **Solve** (`POST /api/scenarios/solve`): Culprit ID check → embedding similarity (threshold 0.7) → LLM fallback if below threshold → weighted score (40% culprit + 60% reasoning).

### Configuration
Environment variables via `.env` file (loaded by `python-dotenv`). Key vars defined in `app/core/config.py`:
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`

### Adding New Components

**New LLM agent**: Create prompt in `app/prompts/{name}/`, output schema in `app/models/schemas/`, agent in `app/services/agent/`. Use `PromptLoader.load()` and `llm.complete()`.

**New API endpoint**: Schema in `app/models/schemas/`, service in `app/services/`, DI function in `app/api/dependencies/`, route in `app/api/routes/`, register router in `app/main.py`.

**New DB model**: ORM in `app/db/models/`, export in `__init__.py`, repository methods in `app/db/repositories/`.

### CI/CD
GitHub Actions (`.github/workflows/ci.yml`) builds and pushes Docker image to GHCR on push to `main`. Target architecture: `linux/arm64`.
