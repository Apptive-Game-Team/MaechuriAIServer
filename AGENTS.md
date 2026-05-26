# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Project Overview

MaechuriAIServer is a Python 3.12 FastAPI backend for an LLM-powered mystery detective game, with Korean-language gameplay as a major focus. It handles scenario generation, map and clue generation, suspect interrogation, pressure tracking, RAG-backed chat context, and solve validation.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload

# Run all tests
pytest app/test/

# Run one test file
pytest app/test/test_embedding.py

# Run one test
pytest app/test/test_embedding.py::test_function_name -v

# Run with Docker
docker-compose up
docker-compose up --build
```

## Architecture

- `app/main.py`: FastAPI application factory, router registration, startup/shutdown lifecycle.
- `app/api/`: HTTP routes, dependencies, and API error handling.
- `app/services/`: business logic and orchestration.
- `app/services/agent/`: LLM-backed generation, roleplay, judging, and validation agents.
- `app/services/llm/`: LLM client abstraction and Gemini implementation.
- `app/services/embedding/`: embedding model loading and embedding service code.
- `app/services/rag/`: indexing, retrieval, context construction, and RAG orchestration.
- `app/services/scenario/`: scenario generation, solve flow, and intermediate state management.
- `app/services/npc/`: chat service and formatting for NPC interactions.
- `app/db/`: async SQLAlchemy models, repositories, Redis, database helpers, and SQL migrations.
- `app/models/domain/`: runtime domain models used across services.
- `app/models/schemas/`: Pydantic request/response and structured LLM output schemas.
- `app/prompts/`: prompt templates loaded by `PromptLoader`.
- `docs/`: endpoint, architecture, CI, and design notes.

## Technology Notes

- FastAPI is async-first; keep route handlers, repository calls, and service boundaries compatible with async SQLAlchemy patterns.
- Pydantic v2 is used for schemas.
- PostgreSQL plus pgvector is used for persistent data and embeddings.
- Redis tracks task state for background scenario generation.
- Gemini is accessed through `google-genai`; keep LLM access behind the `LLMClient` abstraction where practical.
- BGE-M3 embeddings are multilingual and 1024-dimensional.

## Development Guidelines

- Prefer existing dependency-injection factories in `app/api/dependencies/` when wiring routes to services.
- Keep route modules thin. Put business logic in services and data access in repositories.
- When adding an LLM agent, add or update:
  - a prompt under `app/prompts/{agent_name}/`,
  - schemas under `app/models/schemas/` if the output is structured,
  - service code under `app/services/agent/`,
  - tests or demo coverage under `app/test/` when feasible.
- When adding an API endpoint, add schemas first, then service logic, dependency wiring, route registration, and tests.
- When changing database shape, update ORM models and add a numbered SQL migration under `app/db/migrations/`.
- Treat prompt files as part of the product behavior. Keep prompt edits focused and verify structured outputs against their schemas.
- Preserve Korean-language behavior and terminology unless the task explicitly asks for localization changes.
- Do not commit secrets or generated local state. Environment values should come from `.env`.

## Testing Guidance

- Run the smallest relevant pytest target first, then broader tests when changes affect shared services, schemas, repositories, prompts, or API behavior.
- Some tests may require external services, model downloads, database, Redis, or API keys. If a test cannot run locally because of environment requirements, report the blocker explicitly.
- For schema or formatter changes, include direct unit coverage where possible because failures are usually deterministic.

## Configuration

Important environment variables are defined in `app/core/config.py` and loaded through `python-dotenv`, including:

- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`

## Agent Safety

- Before editing, check `git status --short` and avoid overwriting unrelated user changes.
- Create task branches with `<task-character>/ISSUE-<issue-num>`, such as `feat/ISSUE-1`, `refact/ISSUE-2`, or `fix/ISSUE-3`.
- Use `rg` for repository search.
- Keep changes narrowly scoped to the user request.
- Avoid broad refactors unless they are necessary for correctness.
- Do not run destructive git commands unless the user explicitly requests them.
