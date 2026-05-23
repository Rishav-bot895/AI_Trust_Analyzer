# AI Trust Analyzer — Implementation Plan

**Project state**: Phase 1 backend foundation is complete and tested. Phase 2 is in progress (Tasks 2.1-2.3 complete). Treat this document as the execution plan for remaining work.
**Architecture update (mandatory)**: Legacy ChromaDB assumptions are replaced by PostgreSQL + pgvector hosted on Supabase free tier. The product must support two user modes: authenticated users (persistent history) and guest users (ephemeral data deleted when session closes or expires).

**Goal**: Build a full-stack factuality-risk analysis tool. User pastes an AI-generated response, five LangGraph agents (Extractor → Retriever → Verifier → Critic → Judge) analyze it, and a React UI displays trust scores, claim-by-claim verdicts, evidence citations, and an agent execution timeline.
This is decision-support, not definitive hallucination detection; outputs must include transparent confidence labeling and evidence provenance.

**Cross-cutting requirements (apply to all phases/tasks):**
- Vector storage and similarity search must use Supabase PostgreSQL with pgvector only (no ChromaDB runtime dependency).
- All analysis data must be ownership-scoped:
  - Authenticated mode: persist analysis, claims, evidence, and timeline under the authenticated user and expose history endpoints/UI.
  - Guest mode: isolate data by guest session, do not expose cross-session history, and delete guest data after browser session close and TTL-based backend cleanup.
- API and frontend must carry user mode context on every analyze, poll, claims, evidence, timeline, and compare interaction.
- API response/request naming contract must be explicit and uniform end-to-end. Use one canonical wire format (snake_case or camelCase) and enforce deterministic transformations/tests at API boundaries.
- Supabase authentication validation must be production-safe: verify token signature and claims using Supabase-compatible verification strategy (JWKS/asymmetric support), not only shared-secret HS256 assumptions.

---

## Completed Tasks Tracker

Update this section every time a task is completed.

### Phase 1 - Backend Foundation
- [x] 1.1 Initialize FastAPI application in main.py
- [x] 1.2 Implement Settings configuration class in config.py
- [x] 1.3 Add all missing packages to requirements.txt
- [x] 1.4 Create Pydantic schemas for Claim and ClaimStatus
- [x] 1.5 Create Pydantic schemas for Evidence
- [x] 1.6 Create Pydantic schemas for Analysis request and response
- [x] 1.7 Create Pydantic schema for AgentState (LangGraph state)
- [x] 1.8 Set up SQLAlchemy database models and session management
- [x] 1.9 Create Alembic migration for initial database schema
- [x] 1.10 Set up vector store initialization (legacy ChromaDB implementation; superseded by correction tasks)
- [x] 1.11 Wire up the API router in router.py and mount to main.py

### Phase 2 - Agent Implementation
- [x] 2.1 Create agent base utilities and LLM factory
- [x] 2.2 Implement Claim Extractor agent - LLM call and prompt
- [x] 2.3 Implement Claim Extractor agent - output parsing and validation
- [x] 2.4 Implement Retriever agent - Tavily web search
- [x] 2.5 Implement Retriever agent - vector store queries (legacy ChromaDB implementation; superseded by correction tasks)
- [x] 2.6 Implement Retriever agent - deduplication and evidence ranking
- [ ] 2.7 Implement Verifier agent - claim vs evidence comparison
- [ ] 2.8 Implement Verifier agent - per-claim confidence scoring
- [ ] 2.9 Implement Critic agent - logical fallacy and quality analysis
- [ ] 2.10 Implement Critic agent - output formatting and structured critique
- [ ] 2.11 Implement Judge agent - trust score calculation
- [ ] 2.12 Implement Judge agent - hallucination risk and verdict
- [ ] 2.13 Implement LangGraph workflow - state schema and graph setup
- [ ] 2.14 Implement LangGraph workflow - error handling and conditional edges
- [ ] 2.15 Implement LangGraph workflow - async execution and public interface

### Phase 3 - API Routes
- [ ] 3.1 Implement POST /api/v1/analyze route
- [ ] 3.2 Implement GET /api/v1/analyze/{id} route for polling
- [ ] 3.3 Implement GET /api/v1/analyze/{id}/claims route
- [ ] 3.4 Implement GET /api/v1/analyze/{id}/evidence route
- [ ] 3.5 Implement GET /api/v1/analyze/{id}/timeline route
- [ ] 3.6 Implement POST /api/v1/compare route
- [ ] 3.7 Add error handling middleware and rate limiting
- [ ] 3.8 Implement CRUD repository layer for database operations

### Phase 4 - Frontend Components
- [ ] 4.1 Update layout.tsx and application metadata
- [ ] 4.2 Set up global CSS design tokens and Tailwind base styles
- [ ] 4.3 Create TypeScript types matching backend API schemas
- [ ] 4.4 Create API client module with fetch wrapper
- [ ] 4.5 Create useAnalysis and usePolling React hooks
- [ ] 4.6 Build AnalysisInputForm component
- [ ] 4.7 Build TrustScoreCard component
- [ ] 4.8 Build ClaimsTable component with status badges
- [ ] 4.9 Build EvidencePanel component
- [ ] 4.10 Install React Flow and build AgentTimeline component
- [ ] 4.11 Build ModelComparisonTable component
- [ ] 4.12 Build TabNavigation component
- [ ] 4.13 Assemble ResultsView page combining all components
- [ ] 4.14 Replace page.tsx boilerplate with full app layout
- [ ] 4.15 Add loading skeleton states for async content

### Phase 5 - Integration and End-to-End Testing
- [ ] 5.1 Set up pytest fixtures and test database
- [ ] 5.2 Write full-pipeline integration test (happy path)
- [ ] 5.3 Write integration tests for edge cases and error handling
- [ ] 5.4 Set up Vitest and React Testing Library in frontend
- [ ] 5.5 Write frontend unit tests for form and score components
- [ ] 5.6 Write frontend unit tests for table and panel components

### Phase 6 - Database and Storage
- [ ] 6.1 Write production database schema SQL for Supabase
- [ ] 6.2 Configure Supabase connection for development and production

### Phase 7 - Deployment and CI/CD
- [ ] 7.1 Create Dockerfile for the FastAPI backend
- [ ] 7.2 Create docker-compose.yml for local full-stack development
- [ ] 7.3 Create GitHub Actions CI workflow
- [ ] 7.4 Configure Render deployment for backend
- [ ] 7.5 Configure Vercel deployment for frontend
- [ ] 7.6 Write production environment variables documentation

---

## Execution Strategy

**Critical path**: (Phase 1 complete) → Corrections for completed legacy tasks → Phases 2 + 3 + 4 + 6 in parallel → Phase 5 → Phase 7

| Phase | Focus | Can start after |
|-------|-------|-----------------|
| 1 | Backend foundation | Completed |
| 2 | Agent implementation | Phase 1 complete |
| 3 | API routes | Phase 1 complete |
| 4 | Frontend components | Phase 1 complete (mock data OK) |
| 5 | Integration & E2E tests | Phases 2, 3, 4 |
| 6 | Database & storage | Phase 1 complete |
| 7 | Deployment & CI/CD | Phases 2, 3, 4 stable |

**Agent implementation tracks in Phase 2** can be developed in parallel (Tasks 2.4-2.12), but LangGraph wiring (Tasks 2.13-2.15) depends on all five agents being complete.

---

## PHASE 1 — Backend Foundation
> Sequential. Must finish before other phases begin.

---

### Task 1.1 — Initialize FastAPI application in `main.py`
**Complexity**: LOW  
**Files**: `backend/app/main.py`  
**Explanation**: Write the FastAPI app factory with CORS middleware, a lifespan context manager for startup/shutdown hooks, uvicorn entry point, and structured logging.

**Scope**:
- Create `FastAPI` instance with title, version, description metadata
- Add `CORSMiddleware` allowing `http://localhost:3000` in development
- Add `lifespan` async context manager (startup: log app ready; shutdown: log graceful stop)
- Include the main API router from `app.api.router`
- Add root health check `GET /` returning `{"status": "ok"}`
- Configure `logging.basicConfig` with ISO timestamp format
- Add `if __name__ == "__main__"` block running `uvicorn` with reload

**Acceptance Criteria**:
- `uvicorn backend.app.main:app --reload` starts without errors
- `GET /` returns `{"status": "ok"}` with HTTP 200
- CORS headers present on responses to `Origin: http://localhost:3000`
- Log output shows timestamp, level, and message

**Tests**:
- `test_root_health_check` — GET / → 200 `{"status": "ok"}`
- `test_cors_header_present` — response includes `Access-Control-Allow-Origin`
- `test_app_has_title` — `app.title == "AI Trust Analyzer"`
- `test_startup_logs_ready` — startup message captured in logs

---

### Task 1.2 — Implement `Settings` configuration class in `config.py`
**Complexity**: LOW  
**Files**: `backend/app/core/config.py`, `.env.example`  
**Explanation**: Use `pydantic-settings` to define a `Settings` class that reads environment variables, with sensible defaults and validation.

**Scope**:
- Install `pydantic-settings` (add to `requirements.txt`)
- `Settings` class fields: `GEMINI_API_KEY: str`, `TAVILY_API_KEY: str`, `DATABASE_URL: str` (Supabase PostgreSQL URL), `SUPABASE_URL: str`, `SUPABASE_ANON_KEY: str`, `SUPABASE_SERVICE_ROLE_KEY: str`, `SUPABASE_JWT_SECRET: str`, `ENVIRONMENT: str = "development"`, `ALLOWED_ORIGINS: list[str]`, `LOG_LEVEL: str = "INFO"`, `MAX_CLAIMS: int = 50`, `VECTOR_EMBEDDING_DIM: int = 384`, `GUEST_SESSION_TTL_HOURS: int = 24`
- `model_config = SettingsConfig(env_file=".env", env_file_encoding="utf-8")`
- Expose a module-level `settings = Settings()` singleton
- Validate that `GEMINI_API_KEY`, `DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_JWT_SECRET` are non-empty strings

**Acceptance Criteria**:
- `from app.core.config import settings` works without errors
- Missing required API or Supabase settings raise `ValidationError` at import time
- `.env.example` lists every required variable with placeholder values

**Tests**:
- `test_settings_loads_from_env` — monkeypatch env vars, settings reads them
- `test_missing_api_key_raises` — unset key → `ValidationError`
- `test_default_values` — `ENVIRONMENT` defaults to `"development"`
- `test_env_example_contains_all_keys` — parse `.env.example`, compare to `Settings` fields

---

### Task 1.3 — Add all missing packages to `requirements.txt`
**Complexity**: LOW  
**Files**: `requirements.txt`  
**Explanation**: The current file is missing LangGraph, LangChain, Gemini integration, Tavily retrieval tooling, pgvector/PostgreSQL support, SQLAlchemy, Alembic, pydantic-settings, and test tooling. Add exact pinned versions.

**Scope**:
- Add: `langgraph>=0.2`, `langchain>=0.2`, `langchain-google-genai>=2.0`, `langchain-community>=0.2`
- Add: `tavily-python>=0.3`
- Add: `pgvector>=0.2`
- Add: `psycopg[binary]>=3.2`
- Add: `sentence-transformers>=3.0`
- Add: `sqlalchemy>=2.0`, `alembic>=1.13`
- Add: `pydantic-settings>=2.0`
- Add: `asyncpg>=0.30` (async PostgreSQL driver)
- Add: `supabase>=2.0` (Supabase auth/session integration)
- Add: `slowapi>=0.1.9` (API rate limiting)
- Add test dependencies: `pytest>=8.0`, `pytest-asyncio>=0.23`, `httpx>=0.27` (for TestClient), `pytest-cov>=5.0`
- Run `pip install -r requirements.txt` to validate all packages resolve without conflicts

**Acceptance Criteria**:
- `pip install -r requirements.txt` completes without errors
- `import langgraph`, `import pgvector`, `import langchain_google_genai`, `import tavily`, and `import supabase` all succeed
- No version conflicts reported by pip

**Tests**:
- `test_all_imports_resolve` — a test script imports every added package
- `test_no_pip_conflicts` — `pip check` exits with code 0

---

### Task 1.4 — Create Pydantic schemas for `Claim` and `ClaimStatus`
**Complexity**: LOW  
**Files**: `backend/app/schemas/claim.py`  
**Explanation**: Define the data shape for a single extracted claim, including its text, confidence score, and verification status. Support nuanced verification outcomes where a claim can be fully supported, partially supported, contradicted, unsupported, or unverifiable.

**Scope**:
- Create `backend/app/schemas/` directory with `__init__.py`
- `ClaimStatus` enum: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`, `UNSUPPORTED`, `UNVERIFIABLE`
  - `SUPPORTED`: Claim is fully verified by evidence
  - `PARTIALLY_SUPPORTED`: Claim is mostly correct but has some inaccuracies or incomplete parts
  - `CONTRADICTED`: Evidence directly contradicts the claim
  - `UNSUPPORTED`: No evidence found to verify or contradict the claim
  - `UNVERIFIABLE`: Claim is definitional, subjective, or about future events
- `Claim` Pydantic model: `id: UUID`, `text: str`, `confidence: float` (0–1), `status: ClaimStatus`, `claim_index: int`, `source_span: str | None`
- `ClaimCreate` model (no `id`, used for agent output before DB write)
- All fields have docstring descriptions

**Acceptance Criteria**:
- `Claim(**data)` validates correctly with all field types
- `Claim(confidence=1.5)` raises `ValidationError`
- JSON serialization round-trips without data loss

**Tests**:
- `test_claim_valid_construction`
- `test_claim_confidence_out_of_range_raises`
- `test_claim_status_enum_values`
- `test_claim_json_roundtrip`

---

### Task 1.5 — Create Pydantic schemas for `Evidence`
**Complexity**: LOW  
**Files**: `backend/app/schemas/evidence.py`  
**Explanation**: Define the shape for a retrieved evidence piece, including its source URL, snippet text, relevance score, and polarity (whether it supports or contradicts the claim). Evidence polarity is determined by the Verifier agent when comparing evidence against claims.

**Scope**:
- `EvidenceSource` enum: `WEB_SEARCH`, `PGVECTOR`
- `EvidencePolarity` enum: `FOR`, `AGAINST`
  - `FOR`: Evidence supports the claim
  - `AGAINST`: Evidence contradicts the claim
- `Evidence` Pydantic model: `id: UUID`, `claim_id: UUID`, `snippet: str`, `source_url: str | None`, `source_title: str | None`, `relevance_score: float`, `source_type: EvidenceSource`, `polarity: EvidencePolarity | None`, `retrieved_at: datetime`
  - `polarity` is `None` initially (set by Verifier agent), becomes `FOR` or `AGAINST` after verification
- `EvidenceCreate` model (no `id`, `polarity` defaults to `None`)
- URL field validated with `AnyHttpUrl` type

**Acceptance Criteria**:
- `Evidence(**data)` validates with all fields
- Invalid URL raises `ValidationError`
- `source_url: None` is allowed (pgvector-only internal sources may lack URLs)
- `polarity: None` is allowed initially (evidence retrieved before verification)
- Polarity can be set to `FOR` or `AGAINST` after verification

**Tests**:
- `test_evidence_valid_construction`
- `test_evidence_invalid_url_raises`
- `test_evidence_none_url_allowed`
- `test_evidence_source_enum`
- `test_evidence_polarity_enum`
- `test_evidence_polarity_none_allowed`

---

### Task 1.6 — Create Pydantic schemas for `Analysis` request and response
**Complexity**: LOW  
**Files**: `backend/app/schemas/analysis.py`  
**Explanation**: Define the top-level request/response models for the analysis API — what the frontend sends and what it receives back.

**Scope**:
- `AnalysisRequest`: `prompt: str` (max 2000 chars), `response: str` (max 10000 chars), `model_name: str = "gemini-3.1-flash-lite"`, `include_comparison: bool = False`
- `AnalysisStatus` enum: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`
- `AnalysisResponse`: `id: UUID`, `status: AnalysisStatus`, `trust_score: float | None`, `hallucination_risk: str | None`, `claims: list[Claim]`, `evidence: list[Evidence]`, `critique: str | None`, `verdict: str | None`, `created_at: datetime`, `completed_at: datetime | None`, `error: str | None`
- `AnalysisListItem` (summary without nested claims/evidence)

**Acceptance Criteria**:
- `AnalysisRequest(prompt="", response="test")` raises because prompt is empty
- `AnalysisRequest(response="x" * 10001)` raises due to length limit
- `AnalysisResponse` serializes to valid JSON with nested models

**Tests**:
- `test_analysis_request_empty_prompt_raises`
- `test_analysis_request_response_too_long_raises`
- `test_analysis_response_serializes_nested`
- `test_analysis_status_enum`

---

### Task 1.7 — Create Pydantic schema for `AgentState` (LangGraph state)
**Complexity**: LOW  
**Files**: `backend/app/schemas/agent_state.py`  
**Explanation**: Define the shared state dictionary that flows between LangGraph nodes. Every agent reads from and writes to this typed dictionary.

**Scope**:
- `AgentState` as a `TypedDict` with: `analysis_id: str`, `prompt: str`, `response: str`, `model_name: str`, `claims: list[dict]`, `evidence: list[dict]`, `verified_claims: list[dict]`, `critique: str | None`, `trust_score: float | None`, `hallucination_risk: str | None`, `verdict: str | None`, `timeline: list[dict]`, `error: str | None`
- `TimelineEvent` TypedDict: `agent: str`, `started_at: str`, `completed_at: str`, `input_summary: str`, `output_summary: str`

**Acceptance Criteria**:
- Type checker (mypy/pyright) accepts `AgentState` annotations without errors
- Each agent in Phase 2 uses this exact schema without modifications

**Tests**:
- `test_agent_state_typeddict_keys` — assert all required keys exist
- `test_timeline_event_structure`

---

### Task 1.8 — Set up SQLAlchemy database models and session management
**Complexity**: MEDIUM  
**Files**: `backend/app/db/models.py`, `backend/app/db/session.py`, `backend/app/db/__init__.py`  
**Explanation**: Create SQLAlchemy ORM models for persisting analyses, claims, and evidence, plus the async session factory.

**Scope**:
- `Analysis` ORM model: maps to `analyses` table with all `AnalysisResponse` fields plus ownership columns (`user_id` nullable, `guest_session_id` nullable, `is_guest` boolean)
- `Claim` ORM model: maps to `claims` table with foreign key to `analyses.id`
- `Evidence` ORM model: maps to `evidence` table with foreign key to `claims.id`
- Add `ChatSession` ORM model to track per-user and per-guest conversation/session boundaries
- `engine = create_async_engine(settings.DATABASE_URL)` using `asyncpg` against Supabase PostgreSQL
- `AsyncSessionLocal` session factory
- `get_db()` async generator for FastAPI dependency injection

**Acceptance Criteria**:
- `alembic revision --autogenerate` detects the models and generates a migration
- `get_db()` yields a working session and closes it on completion
- Supabase PostgreSQL connection works in development and production environments

**Tests**:
- `test_analysis_model_table_name`
- `test_claim_fk_to_analysis`
- `test_get_db_yields_session`
- `test_get_db_closes_on_exit`

---

### Task 1.9 — Create Alembic migration for initial database schema
**Complexity**: LOW  
**Files**: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/001_initial.py`  
**Explanation**: Initialize Alembic and generate the first migration that creates the `analyses`, `claims`, `evidence`, and `chat_sessions` tables, and enables pgvector.

**Scope**:
- Run `alembic init alembic` inside `backend/`
- Configure `env.py` to import ORM models and use `settings.DATABASE_URL`
- Generate initial migration with `alembic revision --autogenerate -m "initial"`
- Add SQL for `CREATE EXTENSION IF NOT EXISTS vector`
- Verify migration creates all required tables with ownership columns and foreign keys

**Acceptance Criteria**:
- `alembic upgrade head` runs without errors on a fresh PostgreSQL/Supabase database
- `alembic downgrade base` successfully reverses all changes
- All required tables, ownership columns, and pgvector extension exist after upgrade

**Tests**:
- `test_migration_upgrade_creates_tables`
- `test_migration_downgrade_removes_tables`

---

### Task 1.10 — Set up pgvector client utilities and vector index initialization
**Complexity**: LOW  
**Files**: `backend/app/db/vector_store.py`
**Explanation**: Create pgvector helper utilities for inserting evidence embeddings and querying by similarity in Supabase PostgreSQL.

**Scope**:
- Create `evidence_embeddings` table helpers with `embedding vector(VECTOR_EMBEDDING_DIM)`
- Build embeddings using `sentence-transformers` and persist vectors with SQLAlchemy/pgvector
- `add_documents(texts: list[str], metadatas: list[dict], ids: list[str])` function
- `query_similar(query_text: str, n_results: int = 5) -> list[dict]` function using cosine distance `<=>`
- Ensure tenant-safe query filters by `user_id` or `guest_session_id`

**Acceptance Criteria**:
- `add_documents(...)` adds entries to PostgreSQL pgvector without error
- `query_similar("test query")` returns a list of result dicts
- Supabase pgvector data persists across restarts

**Tests**:
- `test_collection_created_on_first_use`
- `test_add_and_query_roundtrip`
- `test_query_returns_n_results`

---

### Task 1.11 — Wire up the API router in `router.py` and mount to `main.py`
**Complexity**: LOW  
**Files**: `backend/app/api/router.py`, `backend/app/main.py`  
**Explanation**: Create the top-level `APIRouter` that will aggregate all route modules, and mount it on the FastAPI app under the `/api/v1` prefix.

**Scope**:
- In `router.py`: create `router = APIRouter(prefix="/api/v1")`
- Import and include sub-routers: `analysis_router`, `comparison_router`, `health_router`
- In `main.py`: `app.include_router(router)`
- Add a placeholder 501 response to each sub-router so routes exist before Phase 3

**Acceptance Criteria**:
- `GET /api/v1/health` returns 200
- `POST /api/v1/analyze` returns 501 (not implemented yet, placeholder)
- All routes visible in `GET /docs` (Swagger UI)

**Tests**:
- `test_router_prefix_applied`
- `test_openapi_schema_includes_analyze`
- `test_health_route_exists`

---

### User Testing Scenarios (Given/When/Then)

1. **Given** I am in the repo root with `.env` configured, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000` and open `http://localhost:8000/docs`, **Then** I should see Swagger load with `/`, `/api/v1/health`, and placeholder analyze/compare routes.
2. **Given** the backend is running on port 8000, **When** I run `curl -i http://localhost:8000/`, **Then** I should get `HTTP/1.1 200` and body `{"status":"ok"}`.
3. **Given** CORS is configured for local frontend, **When** I run `curl -i -H "Origin: http://localhost:3000" http://localhost:8000/`, **Then** the response headers should include `access-control-allow-origin: http://localhost:3000`.
4. **Given** I am in `backend/`, **When** I run `..\.venv\Scripts\python.exe -m alembic upgrade head` and then `..\.venv\Scripts\python.exe -m alembic downgrade base`, **Then** both commands should complete with exit code 0 and no migration exceptions.
5. **Given** pgvector helper functions are available, **When** I run a short script that calls `add_documents(["Mars is the fourth planet"], [{"title":"fact"}], ["doc-1"])` and then `query_similar("Mars", 1)`, **Then** the query should return at least one item containing a non-empty `snippet`.

---

## PHASE 2 — Agent Implementation
> Agent implementation tracks (Tasks 2.4-2.12) can be developed in parallel. LangGraph wiring (Tasks 2.13-2.15) requires all five agents.
> Migration note: Phase 1 is already complete; begin Phase 2 on the Gemini + Tavily (free tier) stack defined in this plan.

---

### Task 2.1 — Create agent base utilities and LLM factory
**Complexity**: LOW  
**Files**: `backend/app/agents/base.py`  
**Explanation**: Shared utilities used by all five agents: an LLM factory that creates `ChatGoogleGenerativeAI` instances (Gemini), a prompt template loader, and a timing decorator for the timeline.

**Scope**:
- `get_llm(model_name: str = "gemini-3.1-flash-lite", temperature: float = 0.0) -> ChatGoogleGenerativeAI`
- `timed_agent(agent_name: str)` decorator that writes a `TimelineEvent` to `state["timeline"]` before and after the wrapped function runs
- `parse_json_response(content: str) -> dict` — strips markdown code fences, then `json.loads`
- Common system prompt snippets stored as constants

**Acceptance Criteria**:
- `get_llm()` returns a `ChatGoogleGenerativeAI` instance with correct model name
- `@timed_agent("extractor")` wrapper adds a timeline entry with start/end timestamps
- `parse_json_response("```json\n{...}\n```")` returns a Python dict

**Tests**:
- `test_get_llm_returns_correct_model`
- `test_timed_agent_adds_timeline_entry`
- `test_parse_json_response_strips_fences`
- `test_parse_json_response_invalid_raises`

---

### Task 2.2 — Implement Claim Extractor agent — LLM call and prompt
**Complexity**: MEDIUM  
**Files**: `backend/app/agents/claim_extractor.py`  
**Explanation**: The first agent in the pipeline. Sends the AI response text to Gemini (`gemini-3.1-flash-lite`) with a structured extraction prompt to get a list of atomic, verifiable claims.

**Scope**:
- System prompt: instructs model to extract atomic factual claims, ignore opinions
- User message: the `state["response"]` text
- Call `get_llm().invoke([system, human])` using `with_structured_output` or forced JSON mode
- The raw LLM output is stored in `state["claims"]` as a list of `{"text": str, "confidence": float}` dicts
- Wrap entire function with `@timed_agent("claim_extractor")`

**Acceptance Criteria**:
- Given a 3-sentence factual paragraph, extracts ≥ 3 distinct claims
- Each claim dict has `"text"` (non-empty string) and `"confidence"` (0–1 float)
- Response containing only opinions returns empty list without error

**Tests**:
- `test_extractor_extracts_claims` (mock LLM response)
- `test_extractor_empty_response_returns_empty_list`
- `test_extractor_opinion_only_returns_empty`
- `test_extractor_timeline_entry_added`

---

### Task 2.3 — Implement Claim Extractor agent — output parsing and validation
**Complexity**: LOW  
**Files**: `backend/app/agents/claim_extractor.py`  
**Explanation**: After the LLM call, parse and validate the raw JSON output, assign UUIDs to each claim, and enforce `MAX_CLAIMS` limit.

**Scope**:
- Call `parse_json_response(content)` on the LLM output
- Validate each claim with the `ClaimCreate` Pydantic schema
- Assign a UUID `id` to each claim
- Truncate to `settings.MAX_CLAIMS` if over limit
- If parsing fails, set `state["error"] = "Claim extraction failed: {msg}"` and return

**Acceptance Criteria**:
- Malformed JSON from LLM sets `state["error"]` instead of crashing
- More than 50 claims → truncated to 50
- All claims have a valid UUID after this step

**Tests**:
- `test_extractor_assigns_uuids`
- `test_extractor_truncates_at_max_claims`
- `test_extractor_malformed_json_sets_error`
- `test_extractor_validates_confidence_range`

---

### Task 2.4 — Implement Retriever agent — Tavily web search
**Complexity**: MEDIUM  
**Files**: `backend/app/agents/retriever.py`  
**Explanation**: For each extracted claim, query the Tavily search API (free tier) to find supporting or contradicting web sources.

**Scope**:
- Import `TavilyClient` from `tavily-python`
- For each claim in `state["claims"]`, run `tavily.search(query=claim["text"], max_results=3)`
- Map Tavily results to `EvidenceCreate` dicts: `{"claim_id": ..., "snippet": ..., "source_url": ..., "source_title": ..., "relevance_score": ..., "source_type": "WEB_SEARCH"}`
- Append all evidence to `state["evidence"]`

**Acceptance Criteria**:
- Given 3 claims, makes ≤ 9 Tavily API calls
- Each evidence dict has all required `EvidenceCreate` fields
- Tavily API error for a single claim is caught; other claims continue processing

**Tests**:
- `test_retriever_calls_tavily_per_claim` (mock Tavily client)
- `test_retriever_maps_tavily_result_to_evidence`
- `test_retriever_partial_failure_continues`
- `test_retriever_timeline_entry_added`

---

### Task 2.5 — Implement Retriever agent — pgvector similarity queries
**Complexity**: MEDIUM  
**Files**: `backend/app/agents/retriever.py`  
**Explanation**: Supplement Tavily results by querying Supabase pgvector for each claim, retrieving semantically similar stored evidence.

**Scope**:
- Import `query_similar` from `app.db.vector_store`
- For each claim, run `query_similar(claim["text"], n_results=3)`
- Map pgvector results to `EvidenceCreate` dicts with `"source_type": "PGVECTOR"`
- Merge with Tavily results already in `state["evidence"]`

**Acceptance Criteria**:
- Vector store evidence is added alongside web search evidence
- If pgvector index is empty, returns no error (empty list merged cleanly)
- Each vector store result has `source_url: None`
- If Tavily fails for a claim, pgvector retrieval still executes for that same claim

**Tests**:
- `test_retriever_queries_vector_store` (mock `query_similar`)
- `test_retriever_empty_vector_store_ok`
- `test_retriever_merges_both_sources`
- `test_retriever_tavily_failure_still_queries_vector_for_claim`

---

### Task 2.6 — Implement Retriever agent — deduplication and evidence ranking
**Complexity**: LOW  
**Files**: `backend/app/agents/retriever.py`  
**Explanation**: Remove duplicate evidence snippets (same URL appearing multiple times) and rank remaining evidence by relevance score descending.

**Scope**:
- Deduplicate by `source_url` (keep highest `relevance_score` duplicate)
- Sort `state["evidence"]` by `relevance_score` descending
- Keep top 10 evidence items per claim maximum
- Assign final UUIDs to each evidence item

**Acceptance Criteria**:
- Duplicate URLs do not appear in final evidence list
- Evidence is sorted highest-relevance first
- Total evidence items ≤ `len(claims) * 10`

**Tests**:
- `test_retriever_deduplicates_by_url`
- `test_retriever_keeps_highest_relevance_on_dupe`
- `test_retriever_sorts_by_relevance`
- `test_retriever_caps_per_claim`

---

### Task 2.7 — Implement Verifier agent — claim vs evidence comparison
**Complexity**: HIGH  
**Files**: `backend/app/agents/verifier.py`  
**Explanation**: The Verifier agent is the heart of the system. For each claim, it shows the LLM the claim text plus its retrieved evidence and asks it to determine a verdict. The Verifier also classifies each evidence item as supporting (`FOR`) or contradicting (`AGAINST`) the claim, enabling nuanced analysis and partially-supported claims.

**Scope**:
- For each claim, gather its evidence snippets from `state["evidence"]`
- Build prompt: `"Claim: {text}\nEvidence:\n{snippets}\nVerdict: SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED | UNSUPPORTED | UNVERIFIABLE\nFor each evidence snippet, classify as FOR (supports) or AGAINST (contradicts) the claim"`
- Call `get_llm()` once per claim (or batch if cost is a concern)
- Parse response to extract:
  - The verdict label (can now be `PARTIALLY_SUPPORTED`)
  - Evidence polarities (FOR/AGAINST) for each evidence item
- Update each claim dict with `"status": ClaimStatus.value`
- Update each evidence dict with `"polarity": EvidencePolarity.value` (FOR or AGAINST)

**Acceptance Criteria**:
- Given a claim with clear supporting evidence, returns `SUPPORTED`
- Given a claim with mostly-correct evidence and one contradicting detail, returns `PARTIALLY_SUPPORTED`
- Given a claim that evidence directly contradicts, returns `CONTRADICTED`
- Given a claim with no retrieved evidence, returns `UNSUPPORTED`
- Invalid LLM verdict defaults to `UNVERIFIABLE` without crashing
- Each evidence item has polarity set to `FOR` or `AGAINST`
- Evidence supporting a contradicted claim is marked `AGAINST`, and vice versa

**Tests**:
- `test_verifier_supported_claim` (mock LLM)
- `test_verifier_partially_supported_claim` (mixed evidence)
- `test_verifier_contradicted_claim`
- `test_verifier_no_evidence_returns_unsupported`
- `test_verifier_invalid_verdict_defaults_to_unverifiable`
- `test_verifier_classifies_evidence_polarity_for` (evidence supports claim)
- `test_verifier_classifies_evidence_polarity_against` (evidence contradicts claim)
- `test_verifier_timeline_entry_added`

---

### Task 2.8 — Implement Verifier agent — per-claim confidence scoring
**Complexity**: LOW  
**Files**: `backend/app/agents/verifier.py`  
**Explanation**: After assigning a verdict, the Verifier also asks the LLM to rate its own confidence (0–1) in the verdict, updating each claim's confidence score.

**Scope**:
- Extend the Verifier prompt to also output a `confidence` float alongside the verdict
- Parse and validate the confidence value (clamp to 0–1 if out of range)
- Update `claim["confidence"]` with the Verifier's value (overrides Extractor's initial confidence)

**Acceptance Criteria**:
- Every verified claim has a `confidence` between 0 and 1 inclusive
- Out-of-range value from LLM (e.g. 1.3) is clamped to 1.0
- Confidence is higher for `SUPPORTED`/`CONTRADICTED` than `UNVERIFIABLE`

**Tests**:
- `test_verifier_updates_confidence`
- `test_verifier_clamps_confidence_out_of_range`
- `test_verifier_confidence_is_float`

---

### Task 2.9 — Implement Critic agent — logical fallacy and quality analysis
**Complexity**: HIGH  
**Files**: `backend/app/agents/critic.py`  
**Explanation**: The Critic agent analyzes the original AI response holistically for logical fallacies, unsupported generalizations, hedging language, and overconfident assertions.

**Scope**:
- System prompt listing 8 logical fallacy types to detect (ad hominem, false dichotomy, hasty generalization, circular reasoning, appeal to authority, post hoc, straw man, slippery slope)
- User message: full `state["response"]` + all claim statuses
- Output: a structured `{"issues": [{"type": str, "quote": str, "explanation": str}], "overall_assessment": str}`
- Parse output to a string critique summary stored in `state["critique"]`
- Also detect hedging language ("may", "might", "could") and flag as `LOW_CONFIDENCE_LANGUAGE`

**Acceptance Criteria**:
- Given response containing a hasty generalization, critique mentions it
- Empty issues list is valid (no fallacies found)
- `state["critique"]` is a non-empty string after running
- Unknown fallacy types do not crash the parser

**Tests**:
- `test_critic_detects_hasty_generalization` (mock LLM)
- `test_critic_empty_issues_valid`
- `test_critic_stores_critique_string`
- `test_critic_detects_hedging_language`
- `test_critic_timeline_entry_added`

---

### Task 2.10 — Implement Critic agent — output formatting and structured critique
**Complexity**: LOW  
**Files**: `backend/app/agents/critic.py`  
**Explanation**: Format the Critic's raw output into a clean markdown string with sections for each issue type, suitable for display in the frontend.

**Scope**:
- Group issues by type
- Format as markdown: `## Logical Issues\n- **Hasty Generalization**: "{quote}" — {explanation}`
- Append `## Overall Assessment` section
- Store formatted string in `state["critique"]`
- If zero issues found, store `"No logical issues detected."`

**Acceptance Criteria**:
- Output is valid markdown with `##` headings
- Each issue includes the quoted text from the original response
- Zero-issue case returns the no-issues string, not empty

**Tests**:
- `test_critic_output_is_markdown`
- `test_critic_groups_by_issue_type`
- `test_critic_zero_issues_message`

---

### Task 2.11 — Implement Judge agent — trust score calculation
**Complexity**: HIGH  
**Files**: `backend/app/agents/judge.py`  
**Explanation**: The Judge synthesizes all signals from the previous agents into a single trust score (0–100) representing how trustworthy the analyzed AI response is. The scoring formula now accounts for partially-supported claims and evidence polarity to provide more nuanced trust assessment.

**Scope**:
- Inputs: `state["verified_claims"]` (with statuses and evidence polarity), `state["critique"]`
- Formula basis: weighted average of claim verdicts accounting for evidence quality:
  - `SUPPORTED`: 1.0 (all evidence is FOR)
  - `PARTIALLY_SUPPORTED`: 0.65 (mixed FOR/AGAINST evidence, majority FOR)
  - `UNSUPPORTED`: 0.4 (no relevant evidence found)
  - `CONTRADICTED`: 0.0 (majority of evidence is AGAINST)
  - `UNVERIFIABLE`: 0.5 (definitional or unfalsifiable)
- Apply evidence polarity scoring: if a claim is marked SUPPORTED/PARTIALLY_SUPPORTED, boost score by 2 points for every 3+ FOR evidence items; if CONTRADICTED/PARTIALLY_SUPPORTED, reduce by 2 points for every 3+ AGAINST evidence items
- Apply critic penalty: subtract 5 points per logical issue found (min 0)
- Final score scaled 0–100 (round to nearest integer)
- Store in `state["trust_score"]`

**Acceptance Criteria**:
- 100% SUPPORTED claims with no critique issues → score near 100
- 100% PARTIALLY_SUPPORTED claims with balanced evidence → score approximately 65
- 100% CONTRADICTED claims → score near 0
- Score never goes below 0 or above 100
- Single claim UNSUPPORTED → score approximately 40
- PARTIALLY_SUPPORTED claim with 5 FOR and 1 AGAINST evidence → receives partial boost vs full SUPPORTED
- Evidence polarity directly influences claim verdict (SUPPORTED only if majority FOR)

**Tests**:
- `test_judge_all_supported_high_score`
- `test_judge_all_partially_supported_mid_score`
- `test_judge_all_contradicted_low_score`
- `test_judge_score_clamped_to_0_100`
- `test_judge_critic_penalty_applied`
- `test_judge_single_unsupported_claim`
- `test_judge_evidence_polarity_boosts_supported`
- `test_judge_evidence_polarity_reduces_contradicted`
- `test_judge_mixed_evidence_counts_toward_partial_support`

---

### Task 2.12 — Implement Judge agent — hallucination risk and verdict
**Complexity**: MEDIUM  
**Files**: `backend/app/agents/judge.py`  
**Explanation**: Convert the numeric trust score into a categorical risk label and generate a human-readable final verdict summary.

**Scope**:
- `hallucination_risk` thresholds: score ≥ 80 → `"LOW"`, score 50–79 → `"MEDIUM"`, score < 50 → `"HIGH"`
- Ask LLM to write a 2-sentence verdict summary referencing the score, risk level, and top issues
- Store in `state["hallucination_risk"]` and `state["verdict"]`
- Wrap entire Judge function with `@timed_agent("judge")`

**Acceptance Criteria**:
- Score 85 → `"LOW"` risk
- Score 45 → `"HIGH"` risk
- Verdict string is 1–3 sentences (not empty)
- Timeline entry recorded

**Tests**:
- `test_judge_risk_low_threshold`
- `test_judge_risk_high_threshold`
- `test_judge_verdict_non_empty`
- `test_judge_timeline_entry_added`

---

### Task 2.13 — Implement LangGraph workflow — state schema and graph setup
**Complexity**: MEDIUM  
**Files**: `backend/app/agents/workflow.py`  
**Explanation**: Initialize the LangGraph `StateGraph` using `AgentState`, register all five agent functions as nodes, and define the sequential edge flow.

**Scope**:
- `from langgraph.graph import StateGraph, END`
- `graph = StateGraph(AgentState)`
- Add nodes: `"extractor"`, `"retriever"`, `"verifier"`, `"critic"`, `"judge"`
- Add edges: `extractor → retriever → verifier → critic → judge → END`
- Set entry point to `"extractor"`
- Compile to `workflow = graph.compile()`

**Acceptance Criteria**:
- `workflow.invoke(initial_state)` calls all five nodes in order
- `state["timeline"]` contains 5 entries after full run
- Graph compiles without errors
- Edge order matches: extractor → retriever → verifier → critic → judge

**Tests**:
- `test_workflow_compiles`
- `test_workflow_executes_all_nodes` (mock each agent)
- `test_workflow_timeline_has_five_entries`
- `test_workflow_edge_order`

---

### Task 2.14 — Implement LangGraph workflow — error handling and conditional edges
**Complexity**: MEDIUM  
**Files**: `backend/app/agents/workflow.py`  
**Explanation**: Add conditional edges that short-circuit to END if any agent sets `state["error"]`, preventing downstream agents from running on corrupted state.

**Scope**:
- Add a `check_error` conditional function: returns `"end"` if `state["error"]` is set, else `"continue"`
- Replace simple edges with `add_conditional_edges` after each node
- On early termination, set `state["trust_score"] = None` and `state["hallucination_risk"] = "UNKNOWN"`
- Log which agent triggered the error

**Acceptance Criteria**:
- If Extractor sets `state["error"]`, Retriever through Judge are NOT called
- If Retriever fails, Verifier through Judge are NOT called
- Final state always has `error` key (None on success)
- Timeline still contains entries for all agents that did run

**Tests**:
- `test_workflow_short_circuits_on_extractor_error`
- `test_workflow_short_circuits_on_retriever_error`
- `test_workflow_error_state_has_none_score`
- `test_workflow_partial_timeline_on_error`

---

### Task 2.15 — Implement LangGraph workflow — async execution and public interface
**Complexity**: LOW  
**Files**: `backend/app/agents/workflow.py`  
**Explanation**: Expose an `async def run_analysis(request: AnalysisRequest) -> AgentState` function that wraps the workflow invocation, builds the initial state, and returns the final state.

**Scope**:
- `async def run_analysis(analysis_id: str, prompt: str, response: str, model_name: str) -> AgentState`
- Build `initial_state: AgentState` from inputs (empty lists for claims/evidence/timeline)
- Call `await workflow.ainvoke(initial_state)` (LangGraph async)
- Return the final `AgentState` dict

**Acceptance Criteria**:
- `await run_analysis(...)` returns a complete `AgentState`
- Function is `async` and awaitable
- `analysis_id` flows through to the final state unchanged

**Tests**:
- `test_run_analysis_is_async`
- `test_run_analysis_returns_agent_state`
- `test_run_analysis_id_preserved`

---

### User Testing Scenarios (Given/When/Then)

1. **Given** Gemini and Tavily keys are set in `.env`, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_claim_extractor.py::test_extractor_extracts_claims -q`, **Then** the test should pass and confirm extracted claims include non-empty `text` and float `confidence`.
2. **Given** retriever web/vector logic is implemented, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_retriever.py::test_retriever_merges_both_sources -q`, **Then** output evidence should include both `WEB_SEARCH` and `PGVECTOR` source types.
3. **Given** retriever resilience is implemented, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_retriever.py::test_retriever_partial_failure_continues -q`, **Then** the test should pass showing one failing claim does not stop processing other claims.
4. **Given** verifier verdict/polarity logic is implemented, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_verifier.py -q`, **Then** I should see tests pass for `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`, and evidence polarity assignment.
5. **Given** full agent workflow is implemented, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_workflow.py::test_workflow_timeline_has_five_entries -q`, **Then** the returned state timeline should contain five ordered events: extractor, retriever, verifier, critic, judge.

---

## PHASE 3 — API Routes
> Can start after Phase 1. Stubs are created in Task 1.11; these tasks fill in the implementations.

---

### Task 3.1 — Implement `POST /api/v1/analyze` route
**Complexity**: MEDIUM  
**Files**: `backend/app/api/routes/analysis.py`  
**Explanation**: Accept an `AnalysisRequest`, create a DB record with `PENDING` status, fire off the LangGraph workflow in a background task, and immediately return the analysis ID. For MVP use FastAPI `BackgroundTask`; for production migration path, move execution to a durable queue worker.

**Scope**:
- Create `analysis_router = APIRouter(prefix="/analyze", tags=["analysis"])`
- `POST /` handler: validate `AnalysisRequest`, create `Analysis` ORM record with `status=PENDING`, return `{"id": analysis_id, "status": "PENDING"}` immediately
- Resolve requester context from JWT/session:
  - authenticated user: attach `user_id`
  - guest user: create/use `guest_session_id` cookie/token and mark `is_guest=true`
- Launch `BackgroundTask` calling `run_analysis(...)` and updating the DB record
- On background task completion: update DB with all results and `status=COMPLETED`
- On background task error: set `status=FAILED`, `error=str(exc)`

**Acceptance Criteria**:
- POST returns within 200ms (does not block on LLM calls)
- Returns `{"id": UUID, "status": "PENDING"}` with HTTP 202
- Background task eventually sets status to `COMPLETED` or `FAILED`
- Invalid request body returns HTTP 422 with validation details

**Tests**:
- `test_post_analyze_returns_202`
- `test_post_analyze_returns_id_and_pending_status`
- `test_post_analyze_invalid_body_returns_422`
- `test_post_analyze_background_task_fires` (mock `run_analysis`)

---

### Task 3.2 — Implement `GET /api/v1/analyze/{id}` route for polling
**Complexity**: LOW  
**Files**: `backend/app/api/routes/analysis.py`  
**Explanation**: Return the current status and full results of an analysis by ID. Used by the frontend to poll until status is COMPLETED or FAILED.

**Scope**:
- `GET /{analysis_id}` handler: query DB for `Analysis` by UUID
- Enforce ownership check: authenticated user can only access own records; guest can only access records within current guest session
- If not found: raise `HTTPException(404)`
- If `PENDING` or `RUNNING`: return `AnalysisResponse` with null result fields
- If `COMPLETED`: return full `AnalysisResponse` with all nested claims/evidence
- If `FAILED`: return `AnalysisResponse` with `error` field set

**Acceptance Criteria**:
- Non-existent ID → HTTP 404
- Pending analysis → 200 with `status: "PENDING"` and null score
- Completed analysis → 200 with all fields populated

**Tests**:
- `test_get_analysis_not_found_returns_404`
- `test_get_analysis_pending_returns_200`
- `test_get_analysis_completed_returns_full_result`
- `test_get_analysis_failed_returns_error`

---

### Task 3.3 — Implement `GET /api/v1/analyze/{id}/claims` route
**Complexity**: LOW  
**Files**: `backend/app/api/routes/analysis.py`  
**Explanation**: Return just the claims list for a completed analysis, with optional filtering by status.

**Scope**:
- `GET /{analysis_id}/claims` with optional `?status=SUPPORTED` query param
- Enforce ownership/session scope before returning claim data
- Query `claims` table filtered by `analysis_id`
- If `status` param provided, filter by `ClaimStatus`
- Return `list[Claim]`
- 404 if analysis not found, 400 if invalid status value

**Acceptance Criteria**:
- Returns all claims when no filter applied
- `?status=SUPPORTED` returns only supported claims
- Invalid status value `?status=BANANA` → HTTP 400

**Tests**:
- `test_get_claims_no_filter`
- `test_get_claims_filter_by_status`
- `test_get_claims_invalid_status_400`
- `test_get_claims_analysis_not_found_404`

---

### Task 3.4 — Implement `GET /api/v1/analyze/{id}/evidence` route
**Complexity**: LOW  
**Files**: `backend/app/api/routes/analysis.py`  
**Explanation**: Return all evidence items for an analysis, optionally filtered by claim ID.

**Scope**:
- `GET /{analysis_id}/evidence` with optional `?claim_id=UUID` query param
- Join `evidence` → `claims` → `analysis_id` for security (can't query evidence from another user's analysis)
- Enforce authenticated ownership or guest-session ownership for every query path
- Return `list[Evidence]` sorted by `relevance_score` descending

**Acceptance Criteria**:
- Returns all evidence for the analysis without filters
- `?claim_id=UUID` filters to that claim's evidence
- Invalid UUID format in `claim_id` → HTTP 422

**Tests**:
- `test_get_evidence_no_filter`
- `test_get_evidence_filter_by_claim_id`
- `test_get_evidence_invalid_claim_uuid_422`

---

### Task 3.5 — Implement `GET /api/v1/analyze/{id}/timeline` route
**Complexity**: LOW  
**Files**: `backend/app/api/routes/analysis.py`  
**Explanation**: Return the agent execution timeline for an analysis, used to render the React Flow visualization in the frontend.

**Scope**:
- `GET /{analysis_id}/timeline`
- Retrieve `timeline` JSON field from the `Analysis` ORM record
- Enforce authenticated ownership or guest-session ownership
- Return `list[TimelineEvent]` in execution order
- If analysis is still PENDING/RUNNING, return partial timeline

**Acceptance Criteria**:
- Completed analysis returns 5 timeline events (one per agent)
- Each event has `agent`, `started_at`, `completed_at`, `input_summary`, `output_summary`
- PENDING analysis returns empty list (not 404)

**Tests**:
- `test_get_timeline_completed_has_five_events`
- `test_get_timeline_pending_returns_empty_list`
- `test_get_timeline_event_structure`

---

### Task 3.6 — Implement `POST /api/v1/compare` route
**Complexity**: MEDIUM  
**Files**: `backend/app/api/routes/comparison.py`  
**Explanation**: Accept a prompt and response, run the full analysis pipeline against multiple free-tier models (Gemini variants), and return all results side by side.

**Scope**:
- `ComparisonRequest`: `prompt: str`, `response: str`, `models: list[str] = ["gemini-3.1-flash-lite"]`
- `ComparisonResponse`: `analyses: list[AnalysisResponse]` (one per model)
- Run each model's analysis concurrently with `asyncio.gather`
- Return all results once all complete (no background task — this is a synchronous wait)

**Acceptance Criteria**:
- 2 models → 2 analyses in response
- Both analyses have `trust_score` populated
- One model failing does not block others; failed entry has `status=FAILED`

**Tests**:
- `test_compare_two_models_returns_two_analyses`
- `test_compare_one_model_fails_others_continue`
- `test_compare_concurrent_execution` (assert both start before either finishes)

---

### Task 3.7 — Add error handling middleware and rate limiting
**Complexity**: LOW  
**Files**: `backend/app/main.py`, `backend/app/api/middleware.py`  
**Explanation**: Add a global exception handler that returns consistent JSON error responses, and add basic rate limiting to prevent abuse.

**Scope**:
- `@app.exception_handler(Exception)` → returns `{"error": "Internal server error", "detail": str(exc)}` with HTTP 500 in dev, generic message in production
- `@app.exception_handler(HTTPException)` → returns `{"error": exc.detail}` with the correct status code
- Add `slowapi` rate limiter: 30 requests/minute per IP on `/api/v1/analyze POST`
- Log every 500 error with full traceback

**Acceptance Criteria**:
- Unhandled exception → HTTP 500 JSON (not HTML traceback)
- Rate limit exceeded → HTTP 429 with `Retry-After` header
- HTTP 404 → `{"error": "Not Found"}` JSON

**Tests**:
- `test_unhandled_exception_returns_500_json`
- `test_http_exception_returns_correct_status`
- `test_rate_limit_returns_429`

---

### Task 3.8 — Implement CRUD repository layer for database operations
**Complexity**: MEDIUM  
**Files**: `backend/app/db/repository.py`  
**Explanation**: Abstract all database reads and writes into a repository module so routes and agents never write raw SQL or ORM queries inline.

**Scope**:
- `create_analysis(db: AsyncSession, request: AnalysisRequest) -> Analysis`
- `create_analysis(db: AsyncSession, request: AnalysisRequest, user_id: UUID | None, guest_session_id: str | None) -> Analysis`
- `get_analysis(db: AsyncSession, analysis_id: UUID) -> Analysis | None`
- `get_analysis_for_requester(db: AsyncSession, analysis_id: UUID, user_id: UUID | None, guest_session_id: str | None) -> Analysis | None`
- `update_analysis_result(db: AsyncSession, analysis_id: UUID, state: AgentState) -> Analysis`
- `update_analysis_status(db: AsyncSession, analysis_id: UUID, status: AnalysisStatus) -> None`
- `create_claims(db: AsyncSession, analysis_id: UUID, claims: list[dict]) -> list[Claim]`
- `create_evidence(db: AsyncSession, claims: list[Claim], evidence: list[dict]) -> list[Evidence]`
- `get_claims(db: AsyncSession, analysis_id: UUID, status: ClaimStatus | None) -> list[Claim]`
- `get_evidence(db: AsyncSession, analysis_id: UUID, claim_id: UUID | None) -> list[Evidence]`
- `delete_guest_session_data(db: AsyncSession, guest_session_id: str) -> None`
- Persist and read `timeline` as structured JSON (not opaque text blobs), with repository methods responsible for serialization/deserialization boundaries

**Acceptance Criteria**:
- All route handlers use repository functions, no raw ORM in routes
- `create_analysis` returns an `Analysis` ORM object with a generated UUID
- `get_analysis` returns `None` for unknown ID (does not raise)

**Tests**:
- `test_create_analysis_returns_orm_object`
- `test_get_analysis_unknown_returns_none`
- `test_update_analysis_result_persists`
- `test_get_claims_filter_works`

---

### User Testing Scenarios (Given/When/Then)

1. **Given** backend is running locally, **When** I run `curl -i -X POST http://localhost:8000/api/v1/analyze -H "Content-Type: application/json" -d "{\"prompt\":\"Explain the Apollo program\",\"response\":\"Apollo 11 landed on the Moon in 1969 and returned safely.\",\"model_name\":\"gemini-3.1-flash-lite\"}"`, **Then** I should receive `HTTP/1.1 202` with JSON containing `id` and `status`=`PENDING`.
2. **Given** I saved the returned analysis id, **When** I poll `curl -i http://localhost:8000/api/v1/analyze/<ANALYSIS_ID>` every 2-3 seconds, **Then** `status` should transition from `PENDING` or `RUNNING` to `COMPLETED` (or `FAILED` with `error`).
3. **Given** status is `COMPLETED`, **When** I run `curl -i http://localhost:8000/api/v1/analyze/<ANALYSIS_ID>/claims?status=SUPPORTED`, **Then** every returned claim item should have `status`=`SUPPORTED`.
4. **Given** status is `COMPLETED`, **When** I run `curl -i http://localhost:8000/api/v1/analyze/<ANALYSIS_ID>/evidence`, **Then** the returned list should be sorted by descending `relevance_score` and each row should include `claim_id`, `snippet`, and `source_type`.
5. **Given** rate limiting is enabled on analyze POST, **When** I submit more than 30 requests in one minute from the same IP, **Then** at least one response should return `HTTP/1.1 429` and include a `Retry-After` header.

---

## PHASE 4 — Frontend Components
> Can start after Phase 1 (use mock/hardcoded data until backend is ready).

---

### Task 4.1 — Update `layout.tsx` and application metadata
**Complexity**: LOW  
**Files**: `frontend/src/app/layout.tsx`  
**Explanation**: Replace the stock "Create Next App" metadata with the actual product name and description, and set up the Inter font for a cleaner UI.

**Scope**:
- Update `metadata.title` to `"AI Trust Analyzer"`
- Update `metadata.description` to `"Detect hallucinations in AI-generated responses"`
- Replace Geist fonts with Inter (add `next/font/google` import)
- Add `<meta name="theme-color">` for browser chrome
- Set `<html lang="en">` (already present — verify)

**Acceptance Criteria**:
- Browser tab shows "AI Trust Analyzer"
- No console font-loading errors
- Inter font renders in the UI

**Tests**:
- `test_layout_has_correct_title` (snapshot or heading assertion)

---

### Task 4.2 — Set up global CSS design tokens and Tailwind base styles
**Complexity**: LOW  
**Files**: `frontend/src/app/globals.css`  
**Explanation**: Define CSS custom properties for the color palette (trust score colors: green/yellow/red), typography scale, and spacing that all components will use.

**Scope**:
- CSS variables: `--color-trust-high: #22c55e`, `--color-trust-medium: #f59e0b`, `--color-trust-low: #ef4444`
- CSS variables: `--color-supported: #16a34a`, `--color-contradicted: #dc2626`, `--color-unsupported: #9ca3af`
- Base `body` styles: `font-family: var(--font-inter)`, `background: #f8fafc`, `color: #1e293b`
- Tailwind `@layer utilities` for custom `trust-score-ring` animation
- Dark mode CSS variables under `@media (prefers-color-scheme: dark)`

**Acceptance Criteria**:
- CSS variables accessible from all components via Tailwind's `var()` syntax
- Dark mode variables defined
- No CSS parse errors in browser

**Tests**:
- Visual regression (optional) or manual verification

---

### Task 4.3 — Create TypeScript types matching backend API schemas
**Complexity**: LOW  
**Files**: `frontend/src/types/api.ts`  
**Explanation**: Define TypeScript interfaces for all data structures returned by the backend API, keeping frontend types in sync with Pydantic models.

**Scope**:
- `ClaimStatus = "SUPPORTED" | "CONTRADICTED" | "UNSUPPORTED" | "UNVERIFIABLE"`
- `EvidenceSource = "WEB_SEARCH" | "PGVECTOR"`
- `AnalysisStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"`
- `HallucinationRisk = "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"`
- `UserMode = "AUTHENTICATED" | "GUEST"`
- `interface Claim { id: string; text: string; confidence: number; status: ClaimStatus; ... }`
- `interface Evidence { id: string; claimId: string; snippet: string; sourceUrl: string | null; ... }`
- `interface AnalysisResponse { id: string; status: AnalysisStatus; trustScore: number | null; claims: Claim[]; evidence: Evidence[]; ... }`
- `interface AnalysisRequest { prompt: string; response: string; modelName?: string; }`
- `interface AnalysisRequest { prompt: string; response: string; modelName?: string; userMode: UserMode; guestSessionId?: string; }`
- `interface TimelineEvent { agent: string; startedAt: string; completedAt: string; inputSummary: string; outputSummary: string; }`

**Acceptance Criteria**:
- TypeScript compiles without type errors when these types are imported
- Field names use camelCase (matching JSON deserialization convention)

**Tests**:
- TypeScript compilation is the test (no runtime tests needed)

---

### Task 4.4 — Create API client module with fetch wrapper
**Complexity**: LOW  
**Files**: `frontend/src/lib/api-client.ts`  
**Explanation**: Centralize all HTTP calls to the backend in a single module, so components never use `fetch` directly.

**Scope**:
- `BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`
- `async function apiPost<T>(path: string, body: unknown): Promise<T>`
- `async function apiGet<T>(path: string): Promise<T>`
- Both functions: set `Content-Type: application/json`, throw `ApiError` on non-2xx status
- Include auth/session propagation:
  - send bearer token when logged in
  - send guest session header or cookie when in guest mode
- Enforce auth/session propagation for **every** exported API function (`submitAnalysis`, `getAnalysis`, `getClaims`, `getEvidence`, `getTimeline`, `compareModels`)
- Add a single normalization layer that converts canonical backend field casing to frontend field casing for all endpoints (not history-only special casing)
- `class ApiError extends Error { status: number; detail: string }`
- Exported functions: `submitAnalysis(req: AnalysisRequest): Promise<{id: string}>`, `getAnalysis(id: string): Promise<AnalysisResponse>`, `getClaims(id: string, status?: ClaimStatus): Promise<Claim[]>`, `getEvidence(id: string, claimId?: string): Promise<Evidence[]>`, `getTimeline(id: string): Promise<TimelineEvent[]>`, `compareModels(req: ComparisonRequest): Promise<ComparisonResponse>`

**Acceptance Criteria**:
- `submitAnalysis` sends POST to `/api/v1/analyze` with correct body
- HTTP 404 throws `ApiError` with `status: 404`
- All functions type-check correctly

**Tests**:
- `test_submit_analysis_sends_correct_request` (mock fetch)
- `test_api_error_thrown_on_404`
- `test_get_analysis_returns_typed_response`
- `test_all_client_calls_include_owner_context_headers`
- `test_analysis_claims_evidence_timeline_are_case_normalized`

---

### Task 4.5 — Create `useAnalysis` and `usePolling` React hooks
**Complexity**: MEDIUM  
**Files**: `frontend/src/hooks/useAnalysis.ts`, `frontend/src/hooks/usePolling.ts`  
**Explanation**: Custom hooks that encapsulate the submit → poll → complete flow so components stay declarative.

**Scope**:
- `usePolling(id: string | null, intervalMs: number)`: polls `getAnalysis(id)` every `intervalMs` ms, stops when status is `COMPLETED` or `FAILED`
- `useAnalysis()`: returns `{ submit, analysis, status, error, isLoading }`, calls `submitAnalysis`, then starts polling
- `useAnalysis()` must respect user mode and include `guestSessionId` for guest calls
- Handle cleanup: clear interval on unmount
- Expose `reset()` function to clear state
- On guest browser session end, trigger best-effort guest cleanup endpoint

**Acceptance Criteria**:
- `submit(request)` sets `isLoading: true` immediately
- Polling stops automatically on `COMPLETED`
- `error` is set if API returns `FAILED` status or throws
- Unmounting during poll does not cause memory leaks

**Tests**:
- `test_use_analysis_submit_sets_loading`
- `test_use_polling_stops_on_completed`
- `test_use_polling_cleans_up_on_unmount`
- `test_use_analysis_sets_error_on_failure`

---

### Task 4.6 — Build `AnalysisInputForm` component
**Complexity**: MEDIUM  
**Files**: `frontend/src/components/AnalysisInputForm.tsx`  
**Explanation**: The primary input UI — two textareas (one for the original prompt, one for the AI response) plus a model selector and submit button.

**Scope**:
- Two `<textarea>` fields: "Original Prompt" and "AI Response to Analyze"
- Character count display for each (with warning color when approaching limits)
- `<select>` for model: options `gemini-3.1-flash-lite`
- "Analyze" submit button — disabled and shows spinner while `isLoading`
- Client-side validation: both fields required, response at least 50 chars
- Inline validation error messages below each field

**Acceptance Criteria**:
- Submit button disabled when either field is empty
- Character count updates on every keystroke
- Form resets after successful submission
- Pressing Enter in textarea does NOT submit (textarea default)

**Tests**:
- `test_submit_button_disabled_when_empty`
- `test_character_count_updates`
- `test_validation_error_shown_on_short_response`
- `test_form_resets_after_submit`

---

### Task 4.7 — Build `TrustScoreCard` component
**Complexity**: MEDIUM  
**Files**: `frontend/src/components/TrustScoreCard.tsx`  
**Explanation**: Displays the numeric trust score (0–100) in a prominent card with an animated circular progress ring color-coded by risk level.

**Scope**:
- SVG circular progress ring (radius 48px, stroke-dashoffset animation on mount)
- Score number displayed in center of ring (large font)
- Color: green (≥80), yellow (50–79), red (<50)
- Risk label badge: `LOW RISK` / `MEDIUM RISK` / `HIGH RISK`
- Skeleton placeholder when `score === null` (PENDING/loading state)
- `verdict` prop: display 1–2 sentence verdict below the ring

**Acceptance Criteria**:
- Score 85 renders green ring and "LOW RISK" badge
- Score 40 renders red ring and "HIGH RISK" badge
- Null score shows animated skeleton (not 0)
- Ring animates from 0 to final score on first render

**Tests**:
- `test_trust_score_high_renders_green`
- `test_trust_score_low_renders_red`
- `test_null_score_shows_skeleton`
- `test_verdict_text_displayed`

---

### Task 4.8 — Build `ClaimsTable` component with status badges
**Complexity**: MEDIUM  
**Files**: `frontend/src/components/ClaimsTable.tsx`  
**Explanation**: A sortable, filterable table listing all extracted claims with their verification status, confidence score, and expandable detail row.

**Scope**:
- Table with columns: #, Claim Text, Status, Confidence
- Status badge colors: green (SUPPORTED), red (CONTRADICTED), gray (UNSUPPORTED), yellow (UNVERIFIABLE)
- Confidence shown as a mini progress bar
- Clicking a row expands it to show evidence snippets linked to that claim
- Filter buttons: "All", "Supported", "Contradicted", "Unsupported"
- Sort by Confidence (asc/desc)
- Empty state message when no claims

**Acceptance Criteria**:
- Clicking filter "Contradicted" hides non-contradicted claims
- Expanded row shows at least one evidence snippet
- Sort toggles on second click of same column header
- Empty claims list shows "No claims extracted" message

**Tests**:
- `test_claims_table_renders_all_claims`
- `test_claims_filter_by_status`
- `test_claims_expand_shows_evidence`
- `test_claims_sort_by_confidence`
- `test_claims_empty_state_message`

---

### Task 4.9 — Build `EvidencePanel` component
**Complexity**: MEDIUM  
**Files**: `frontend/src/components/EvidencePanel.tsx`  
**Explanation**: A panel displaying all retrieved evidence grouped by claim, with source URLs, snippet text, relevance scores, and source type badges.

**Scope**:
- Group evidence cards by `claimId`
- Each card: snippet text (truncated to 200 chars with "Show more"), source title, URL link (opens in new tab), relevance score chip, source type badge (`WEB` / `VECTOR`)
- No evidence for a claim → show "No evidence retrieved"
- Relevance score color: green (>0.7), yellow (0.4–0.7), gray (<0.4)

**Acceptance Criteria**:
- Evidence grouped correctly under their parent claim
- URL links have `target="_blank" rel="noopener noreferrer"`
- "Show more" expands full snippet text
- PGVECTOR items do not render broken null URL

**Tests**:
- `test_evidence_grouped_by_claim`
- `test_evidence_url_opens_new_tab`
- `test_evidence_show_more_expands`
- `test_evidence_null_url_not_rendered`

---

### Task 4.10 — Install React Flow and build `AgentTimeline` component
**Complexity**: HIGH  
**Files**: `frontend/src/components/AgentTimeline.tsx`, `frontend/package.json`  
**Explanation**: A React Flow canvas showing the five agents as nodes, connected by directed edges, with each node's execution status and timing visible.

**Scope**:
- `npm install @xyflow/react` (add to `package.json`)
- 5 nodes: Extractor, Retriever, Verifier, Critic, Judge — laid out left-to-right
- Directed edges between consecutive agents
- Each node: agent name, duration (`completedAt - startedAt` in ms), status icon (check / spinner / error)
- Tooltip on hover: `inputSummary` and `outputSummary`
- If timeline is empty (PENDING), all nodes show as "waiting" state

**Acceptance Criteria**:
- All 5 nodes visible in the canvas
- Edges flow left-to-right in correct order
- Completed nodes show green checkmark and duration
- PENDING state shows all nodes as gray "waiting"

**Tests**:
- `test_timeline_renders_five_nodes`
- `test_timeline_pending_shows_waiting`
- `test_timeline_completed_node_shows_duration`

---

### Task 4.11 — Build `ModelComparisonTable` component
**Complexity**: MEDIUM  
**Files**: `frontend/src/components/ModelComparisonTable.tsx`  
**Explanation**: A comparison table showing side-by-side results for multiple models: trust score, hallucination risk, claim counts per status, and cost estimate.

**Scope**:
- Columns: Model Name, Trust Score, Risk Level, Supported Claims, Contradicted Claims, Unsupported Claims, Verdict
- Highlight the highest trust score row with a gold border
- Sort by Trust Score (descending) by default
- Delta indicator: show `+12` / `-8` vs. the baseline model (first in list)
- Empty comparison state: "Run a comparison to see results"

**Acceptance Criteria**:
- Highest trust score row highlighted
- Delta shown for all models except baseline
- Sorting works on Trust Score column
- Empty state shown when no comparison data

**Tests**:
- `test_comparison_highlights_best_model`
- `test_comparison_shows_delta`
- `test_comparison_sort_by_score`
- `test_comparison_empty_state`

---

### Task 4.12 — Build `TabNavigation` component
**Complexity**: LOW  
**Files**: `frontend/src/components/TabNavigation.tsx`  
**Explanation**: A tab bar allowing users to switch between Claims, Evidence, Agent Timeline, and Model Comparison views in the results panel.

**Scope**:
- Tabs: `Claims` (with badge count), `Evidence` (with count), `Timeline`, `Compare`, `History`
- Active tab highlighted with bottom border and bold text
- URL hash sync: `#claims`, `#evidence`, `#timeline`, `#compare`
- Keyboard navigation: arrow keys move between tabs
- Disabled state for "Compare" when no comparison data loaded
- `History` tab is visible only for authenticated users

**Acceptance Criteria**:
- Clicking tab changes active content
- URL hash updates on tab change
- Page refresh restores active tab from hash
- Keyboard navigation works

**Tests**:
- `test_tab_click_changes_active`
- `test_tab_hash_sync`
- `test_tab_keyboard_navigation`
- `test_tab_disabled_compare_without_data`

---

### Task 4.13 — Assemble `ResultsView` page combining all components
**Complexity**: MEDIUM  
**Files**: `frontend/src/components/ResultsView.tsx`  
**Explanation**: The results layout: TrustScoreCard at the top, CritiqueSection below it, then the TabNavigation with all four content panels.

**Scope**:
- `ResultsView` accepts `analysis: AnalysisResponse` prop
- Top section: `TrustScoreCard` + critique markdown display
- Tab content: `ClaimsTable`, `EvidencePanel`, `AgentTimeline`, `ModelComparisonTable`
- Add authenticated-only history panel showing previous analyses and claim summaries
- Use `react-markdown` to render the critique field
- Loading skeleton for whole component when `analysis.status !== "COMPLETED"`

**Acceptance Criteria**:
- All four subcomponents render with real data
- Critique markdown renders with correct heading styles
- Loading skeleton matches final layout dimensions (no layout shift)

**Tests**:
- `test_results_view_renders_score_card`
- `test_results_view_renders_all_tabs`
- `test_results_view_loading_shows_skeleton`
- `test_critique_markdown_renders_headings`

---

### Task 4.14 — Replace `page.tsx` boilerplate with full app layout
**Complexity**: MEDIUM  
**Files**: `frontend/src/app/page.tsx`  
**Explanation**: Wire up `AnalysisInputForm`, `useAnalysis` hook, and `ResultsView` into the main page. This is the final assembly of the frontend.

**Scope**:
- Import and use `useAnalysis` hook
- Render `AnalysisInputForm` in top half with `onSubmit={submit}` and `isLoading`
- Conditionally render `ResultsView` below when `analysis` is available
- Add a site header with the product name and a subtle logo
- Add user mode controls: authenticated identity badge or guest mode badge
- Add a footer with GitHub link

**Acceptance Criteria**:
- Fresh page load shows only input form (no results panel)
- After submit, spinner appears in button
- After completion, results panel slides into view
- Header/footer present and styled

**Tests**:
- `test_page_initial_state_shows_form_only`
- `test_page_submit_shows_loading`
- `test_page_completed_shows_results`

---

### Task 4.15 — Add loading skeleton states for async content
**Complexity**: LOW  
**Files**: `frontend/src/components/Skeleton.tsx`, all result components  
**Explanation**: Create a reusable `Skeleton` component and integrate it into every result component to prevent jarring layout shifts during data loading.

**Scope**:
- `<Skeleton width height className>` component using Tailwind `animate-pulse`
- `<SkeletonCard>` preset for evidence cards
- `<SkeletonRow>` preset for table rows
- Integrate skeletons into: `TrustScoreCard`, `ClaimsTable`, `EvidencePanel`

**Acceptance Criteria**:
- All result components show skeleton before data arrives
- Skeleton dimensions match final content dimensions
- `animate-pulse` CSS visible in browser

**Tests**:
- `test_skeleton_renders_with_pulse`
- `test_trust_score_card_shows_skeleton_when_null`
- `test_claims_table_shows_skeleton_rows`

---

### User Testing Scenarios (Given/When/Then)

1. **Given** I started frontend with `cd frontend && npm run dev`, **When** I open `http://localhost:3000`, **Then** I should see header branding, `Original Prompt` textarea, `AI Response to Analyze` textarea, model selector, and disabled Analyze button until both fields are valid.
2. **Given** the page is open, **When** I paste prompt `Explain why the sky is blue` and a 50+ character response, **Then** character counters should update live and Analyze becomes enabled.
3. **Given** I click Analyze once, **When** the request is in progress, **Then** the button should show loading state, remain disabled, and no duplicate request should fire on extra clicks.
4. **Given** analysis data is returned, **When** the results section appears, **Then** TrustScoreCard should show numeric score, matching risk badge color (green >=80, yellow 50-79, red <50), and verdict text.
5. **Given** claims, evidence, and timeline tabs are available, **When** I switch tabs, apply claim filters, and expand a claim row, **Then** tab hash should update (`#claims`/`#evidence`/`#timeline`), filtered rows should change, and timeline should display five connected nodes.

---

## PHASE 5 — Integration & End-to-End Testing

---

### Task 5.1 — Set up pytest fixtures and test database
**Complexity**: LOW  
**Files**: `backend/tests/conftest.py`  
**Explanation**: Configure pytest with shared fixtures: a TestClient, a PostgreSQL test database with pgvector extension, and LLM mocks to prevent real API calls during tests.

**Scope**:
- `@pytest.fixture async def async_client()` using `httpx.AsyncClient` with `ASGITransport`
- `@pytest.fixture` for PostgreSQL test schema with `CREATE EXTENSION IF NOT EXISTS vector` (overrides `settings.DATABASE_URL`)
- `@pytest.fixture` for mock LLM (returns canned responses via `unittest.mock.patch`)
- `@pytest.fixture` for mock Tavily client
- `@pytest.fixture` for authenticated JWT and guest session identifiers
- `pytest.ini` or `pyproject.toml` section: `asyncio_mode = "auto"`, coverage settings

**Acceptance Criteria**:
- `pytest backend/tests/` runs without requiring real API keys
- All fixtures available without explicit import in test files

**Tests**:
- `test_fixtures_load` — fixture imports resolve
- `test_mock_llm_returns_canned_response`

---

### Task 5.2 — Write full-pipeline integration test (happy path)
**Complexity**: MEDIUM  
**Files**: `backend/tests/test_integration.py`  
**Explanation**: Submit a real analysis request end-to-end through the API (with mocked Gemini LLM/Tavily), poll until complete, and assert all fields are populated.

**Scope**:
- POST `/api/v1/analyze` with a sample prompt and response
- Poll `GET /api/v1/analyze/{id}` until `status == "COMPLETED"` (with timeout)
- Assert `trust_score` is between 0 and 100
- Assert `claims` list is non-empty
- Assert `evidence` list is non-empty
- Assert `timeline` has 5 entries
- Assert `verdict` is a non-empty string

**Acceptance Criteria**:
- Test completes within 10 seconds (mocked LLM, no real API calls)
- All assertions pass
- Test is deterministic (no randomness)

**Tests**:
- `test_full_pipeline_happy_path`
- `test_full_pipeline_all_fields_present`
- `test_full_pipeline_timeline_completeness`

---

### Task 5.3 — Write integration tests for edge cases and error handling
**Complexity**: MEDIUM  
**Files**: `backend/tests/test_integration.py`  
**Explanation**: Test error cases: empty input, LLM failures, and retrieval failures to verify the system degrades gracefully.

**Scope**:
- Test: empty `prompt` field → HTTP 422
- Test: LLM throws `RateLimitError` → analysis status becomes `FAILED` with error message
- Test: Tavily returns 0 results → analysis completes but evidence list is empty
- Test: unknown analysis ID → HTTP 404
- Test: `trust_score` in completed analysis is between 0 and 100
- Test: authenticated user cannot access another authenticated user's analysis
- Test: guest user cannot access another guest session's analysis
- Test: guest session cleanup deletes claims/evidence/history for that session
- Test: contract consistency for analysis payload fields (chosen canonical casing) across analyze/poll/claims/evidence/timeline
- Test: Supabase-style JWT validation rejects invalid issuer/audience/signature combinations and accepts valid tokens

**Tests**:
- `test_empty_prompt_returns_422`
- `test_llm_rate_limit_sets_failed_status`
- `test_no_evidence_completes_without_crash`
- `test_unknown_id_returns_404`
- `test_trust_score_within_bounds`

---

### Task 5.4 — Set up Vitest and React Testing Library in frontend
**Complexity**: LOW  
**Files**: `frontend/vitest.config.ts`, `frontend/package.json`, `frontend/src/test/setup.ts`  
**Explanation**: Install and configure Vitest with jsdom and React Testing Library so frontend components can be unit tested.

**Scope**:
- `npm install -D vitest @vitest/ui jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom`
- `vitest.config.ts`: `environment: "jsdom"`, `setupFiles: "./src/test/setup.ts"`, `globals: true`
- `setup.ts`: `import "@testing-library/jest-dom"`
- Add `"test": "vitest"` and `"test:ui": "vitest --ui"` to `package.json` scripts
- Add `"coverage": "vitest run --coverage"` script

**Acceptance Criteria**:
- `npm test` runs without errors (even if no tests exist yet)
- `@testing-library/jest-dom` matchers available globally

**Tests**:
- `test_vitest_config_loads` — a trivial `expect(1).toBe(1)` test

---

### Task 5.5 — Write frontend unit tests for form and score components
**Complexity**: MEDIUM  
**Files**: `frontend/src/components/__tests__/AnalysisInputForm.test.tsx`, `frontend/src/components/__tests__/TrustScoreCard.test.tsx`  
**Explanation**: Unit tests for the two most critical UI components using React Testing Library and mocked fetch.

**Scope**:
- `AnalysisInputForm` tests (from Task 4.6 acceptance criteria)
- `TrustScoreCard` tests (from Task 4.7 acceptance criteria)
- Mock `api-client.ts` module with `vi.mock`
- Use `userEvent` for realistic user interaction simulation

**Acceptance Criteria**:
- All tests in Tasks 4.6 and 4.7 pass
- No real HTTP requests made during tests

**Tests**: All tests listed in Tasks 4.6 and 4.7

---

### Task 5.6 — Write frontend unit tests for table and panel components
**Complexity**: MEDIUM  
**Files**: `frontend/src/components/__tests__/ClaimsTable.test.tsx`, `frontend/src/components/__tests__/EvidencePanel.test.tsx`  
**Explanation**: Unit tests for claims table (filtering, sorting, expand) and evidence panel (grouping, links).

**Scope**:
- `ClaimsTable` tests (from Task 4.8 acceptance criteria)
- `EvidencePanel` tests (from Task 4.9 acceptance criteria)
- Use mock `Claim[]` and `Evidence[]` fixture data

**Acceptance Criteria**: All tests listed in Tasks 4.8 and 4.9 pass.

---

### User Testing Scenarios (Given/When/Then)

1. **Given** I am in repo root and using project venv, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_integration.py -q`, **Then** tests should run without requiring live Gemini/Tavily credentials.
2. **Given** happy-path integration tests exist, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_integration.py::test_full_pipeline_happy_path -q`, **Then** the completed analysis payload should include `trust_score`, non-empty `claims`, non-empty `evidence`, `timeline` length 5, and non-empty `verdict`.
3. **Given** validation-edge tests exist, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_integration.py::test_empty_prompt_returns_422 -q`, **Then** the assertion should confirm API returns 422 for empty prompt payloads.
4. **Given** failure-path tests exist, **When** I run `d:\Project\AI_Trust_Analyzer\.venv\Scripts\python.exe -m pytest backend\tests\test_integration.py::test_llm_rate_limit_sets_failed_status -q`, **Then** the assertion should confirm status becomes `FAILED` and includes a readable error.
5. **Given** frontend unit tests are configured, **When** I run `cd frontend && npm test -- --run`, **Then** component suites for form, score card, claims table, and evidence panel should pass without real network calls.

---

## PHASE 6 — Database & Storage

---

### Task 6.1 — Write production database schema SQL for Supabase
**Complexity**: LOW  
**Files**: `backend/db/schema.sql`  
**Explanation**: Write the raw SQL schema for PostgreSQL/Supabase that matches the SQLAlchemy ORM models, including pgvector, indexes, constraints, ownership fields, and retention metadata.

**Scope**:
- `CREATE TABLE analyses (id UUID PRIMARY KEY, status VARCHAR, trust_score FLOAT, ...)` with all columns
- `CREATE EXTENSION IF NOT EXISTS vector`
- `CREATE TABLE chat_sessions (...)` for authenticated and guest session tracking
- `CREATE TABLE claims (id UUID PRIMARY KEY, analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE, ...)`
- `CREATE TABLE evidence (id UUID PRIMARY KEY, claim_id UUID REFERENCES claims(id) ON DELETE CASCADE, ...)`
- `CREATE TABLE evidence_embeddings (evidence_id UUID PRIMARY KEY REFERENCES evidence(id) ON DELETE CASCADE, embedding vector(384), user_id UUID NULL, guest_session_id TEXT NULL)`
- `analyses.timeline` stored as `JSONB` (array of timeline events), not plain text
- `evidence_embeddings.evidence_id` typed as `UUID` foreign key to `evidence.id` (no untyped TEXT fallback in production schema)
- Indexes on `analyses.status`, `claims.analysis_id`, `evidence.claim_id`
- IVFFlat or HNSW index on `evidence_embeddings.embedding`
- `CREATED_AT` default to `NOW()`

**Acceptance Criteria**:
- Schema SQL executes without errors on PostgreSQL 15
- All foreign keys have CASCADE delete and ownership constraints
- Indexes present for expected query patterns

**Tests**:
- `test_schema_sql_executes_clean` (run against test PostgreSQL)

---

### Task 6.2 — Configure Supabase connection for development and production
**Complexity**: LOW  
**Files**: `backend/app/db/session.py`, `backend/app/core/config.py`  
**Explanation**: Make Supabase PostgreSQL + pgvector the default for both development and production environments, with optional local PostgreSQL fallback if needed.

**Scope**:
- Always use `postgresql+asyncpg://...` for app runtime in both development and production
- `.env` defaults should target a Supabase project connection string (free tier)
- Production `DATABASE_URL` format: `postgresql+asyncpg://user:pass@host/db`
- Document Supabase connection string format in `.env.example`

**Acceptance Criteria**:
- Development and production both run against Supabase PostgreSQL with pgvector enabled
- Environment switching requires only changing `.env` values and Supabase project references

**Tests**:
- `test_supabase_url_uses_asyncpg`
- `test_pgvector_extension_available`

---

### User Testing Scenarios (Given/When/Then)

1. **Given** PostgreSQL 15 is running locally (or Supabase SQL editor is open), **When** I execute `backend/db/schema.sql`, **Then** `analyses`, `claims`, and `evidence` tables plus expected indexes should be created without SQL errors.
2. **Given** those tables contain linked rows, **When** I run `DELETE FROM analyses WHERE id = '<ANALYSIS_UUID>';`, **Then** rows in `claims` and `evidence` tied to that analysis should be removed automatically by `ON DELETE CASCADE`.
3. **Given** `.env` has Supabase values and `DATABASE_URL=postgresql+asyncpg://...`, **When** I start backend with uvicorn, **Then** startup should succeed using Supabase PostgreSQL.
4. **Given** `.env` has `ENVIRONMENT=production` and `DATABASE_URL=postgresql+asyncpg://...`, **When** I start backend and call `GET /api/v1/health`, **Then** the app should respond 200 while using PostgreSQL connection settings.
5. **Given** I change only Supabase project credentials in `.env`, **When** I restart the service each time, **Then** the app should switch database targets with no source-code changes.

---

## PHASE 7 — Deployment & CI/CD

---

### Task 7.1 — Create `Dockerfile` for the FastAPI backend
**Complexity**: LOW  
**Files**: `backend/Dockerfile`, `backend/.dockerignore`  
**Explanation**: Multi-stage Docker build for the backend: a slim Python image that installs dependencies and runs uvicorn.

**Scope**:
- Base: `python:3.12-slim`
- `WORKDIR /app`
- `COPY requirements.txt .` → `RUN pip install --no-cache-dir -r requirements.txt`
- `COPY app/ ./app/`
- `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- `.dockerignore`: exclude `__pycache__`, `.env`, `*.pyc`, `.venv`, `data/`
- Expose port 8000

**Acceptance Criteria**:
- `docker build -t ai-trust-backend .` completes without errors
- `docker run -p 8000:8000 ai-trust-backend` starts the server
- Image size < 500MB

**Tests**:
- `test_docker_build_succeeds` (CI step)
- `test_docker_container_health_check`

---

### Task 7.2 — Create `docker-compose.yml` for local full-stack development
**Complexity**: LOW  
**Files**: `docker-compose.yml`  
**Explanation**: A compose file that starts the FastAPI backend and the Next.js frontend together with a single command. Runtime vectors are stored in Supabase pgvector; optional local PostgreSQL+pgvector service can be enabled for offline development.

**Scope**:
- `backend` service: builds from `backend/Dockerfile`, port 8000, env_file `.env`
- `frontend` service: `node:20-alpine`, runs `npm run dev`, port 3000, depends on backend
- Health checks for both services
- `NEXT_PUBLIC_API_URL=http://backend:8000` env var in frontend service

**Acceptance Criteria**:
- `docker-compose up` starts both services
- Frontend at `localhost:3000` can reach backend at `localhost:8000`
- When local PostgreSQL profile is used, pgvector data persists via a mounted Postgres volume

---

### Task 7.3 — Create GitHub Actions CI workflow
**Complexity**: LOW  
**Files**: `.github/workflows/ci.yml`  
**Explanation**: Automated CI that runs backend tests, frontend lint, and frontend type-check on every push and pull request.

**Scope**:
- Trigger: `push` to `main`, all `pull_request` events
- Job `backend-test`: Python 3.12, `pip install -r requirements.txt`, `pytest --cov=app --cov-report=xml`
- Job `frontend-check`: Node 20, `npm ci`, `npm run lint`, `tsc --noEmit`, `npm test -- --run`
- Upload coverage to Codecov (optional, add if token available)
- Fail fast: if `backend-test` fails, `frontend-check` still runs

**Acceptance Criteria**:
- Workflow file is valid YAML (passes `actionlint`)
- Both jobs run in parallel
- Test failure causes the PR check to fail

---

### Task 7.4 — Configure Render deployment for backend
**Complexity**: LOW  
**Files**: `render.yaml`  
**Explanation**: A `render.yaml` blueprint file so the backend can be deployed to Render.com with one click, with all required environment variable placeholders.

**Scope**:
- Service type: `web`, environment: `python`, buildCommand: `pip install -r requirements.txt`, startCommand: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variables: `GEMINI_API_KEY` (sync from Render secret), `TAVILY_API_KEY`, `DATABASE_URL`, `ENVIRONMENT=production`
- Health check path: `/`
- Free tier instance type

**Acceptance Criteria**:
- Render accepts `render.yaml` without errors
- All required env vars listed as `sync: false` (user must set them)

---

### Task 7.5 — Configure Vercel deployment for frontend
**Complexity**: LOW  
**Files**: `frontend/vercel.json`  
**Explanation**: A `vercel.json` configuration file that sets up the Next.js frontend deployment on Vercel, pointing the API proxy to the Render backend URL.

**Scope**:
- `framework: "nextjs"`
- Rewrite rule: `/api/v1/:path*` → `https://<render-backend-url>/api/v1/:path*` (avoids CORS in production)
- Set `NEXT_PUBLIC_API_URL` environment variable placeholder
- `outputDirectory: ".next"`

**Acceptance Criteria**:
- `vercel.json` is valid JSON (passes `vercel pull` validation)
- Rewrite rule proxies API calls correctly in production

---

### Task 7.6 — Write production environment variables documentation
**Complexity**: LOW  
**Files**: `.env.example`, `README.md` (update)  
**Explanation**: Document every environment variable the project needs, where to obtain the value, and which service requires it.

**Scope**:
- `.env.example` with comments for every variable:
  ```
  # Gemini API key — get from Google AI Studio: https://aistudio.google.com/app/apikey
  GEMINI_API_KEY=AIza...
  ```
- README section "Environment Variables" table: Variable | Required | Default | Description
- README section "Deployment" with step-by-step Render + Vercel instructions

**Acceptance Criteria**:
- Every variable in `Settings` class has a corresponding entry in `.env.example`
- No real secrets committed to the repository

---

### User Testing Scenarios (Given/When/Then)

1. **Given** `backend/Dockerfile` is ready, **When** I run `docker build -t ai-trust-backend ./backend` and `docker run --rm -p 8000:8000 ai-trust-backend`, **Then** `curl -i http://localhost:8000/` should return `HTTP/1.1 200` with `{"status":"ok"}`.
2. **Given** `docker-compose.yml` is configured, **When** I run `docker compose up --build`, **Then** frontend should load at `http://localhost:3000` and backend health should respond at `http://localhost:8000/`.
3. **Given** `.github/workflows/ci.yml` is committed on a feature branch, **When** I push that branch and open a PR, **Then** GitHub Actions should run both backend and frontend jobs and mark the check failed if either job fails.
4. **Given** Render backend and Vercel frontend projects are connected to the repo, **When** I set required env vars and deploy both, **Then** opening the Vercel URL and submitting an analysis should reach the Render API successfully.
5. **Given** `.env.example` and README env docs are complete, **When** a new developer clones the repo and follows only documented steps, **Then** they should be able to run backend, frontend, and tests without undocumented configuration.

---

## Summary

| Phase | Tasks | Complexity |
|-------|-------|-----------|
| 1 — Backend Foundation | 1.1–1.11 (11 tasks) | LOW–MEDIUM |
| 2 — Agent Implementation | 2.1–2.15 (15 tasks) | LOW–HIGH |
| 3 — API Routes | 3.1–3.8 (8 tasks) | LOW–MEDIUM |
| 4 — Frontend Components | 4.1–4.15 (15 tasks) | LOW–HIGH |
| 5 — Integration & Testing | 5.1–5.6 (6 tasks) | LOW–MEDIUM |
| 6 — Database & Storage | 6.1–6.2 (2 tasks) | LOW |
| 7 — Deployment | 7.1–7.6 (6 tasks) | LOW |
| Corrections — Retrofit Completed Work | C.1–C.11 (11 tasks) | MEDIUM |
| **Total** | **74 tasks** | |

---

## Correction Tasks For Already Completed Work (Retrofit)

These tasks correct already-completed legacy items so the implementation matches the updated architecture.

### C.1 — Replace ChromaDB dependency and runtime usage with pgvector
**Applies to completed tasks**: 1.3, 1.10, 2.5  
**Files**: `requirements.txt`, `backend/app/db/vector_store.py`, `backend/app/agents/retriever.py`, relevant tests  
**Scope**:
- Remove `chromadb` usage from code and imports
- Add/verify `pgvector`, `psycopg[binary]`, and Supabase-compatible dependencies
- Update retriever vector evidence `source_type` to `PGVECTOR`

### C.2 — Retrofit settings and env contract for Supabase + guest retention
**Applies to completed tasks**: 1.2  
**Files**: `backend/app/core/config.py`, `.env.example`, tests  
**Scope**:
- Add required Supabase settings and validation
- Add guest-session retention settings (`GUEST_SESSION_TTL_HOURS`)
- Remove deprecated Chroma-specific settings

### C.3 — Add migration for pgvector extension and embedding table
**Applies to completed tasks**: 1.9, 1.10  
**Files**: `backend/alembic/versions/*.py`, `backend/db/schema.sql`  
**Scope**:
- Create Alembic revision enabling vector extension
- Add `evidence_embeddings` and vector index
- Ensure downgrade path safely drops vector artifacts

### C.4 — Retrofit evidence schema source type and contracts
**Applies to completed tasks**: 1.5, 4.3  
**Files**: `backend/app/schemas/evidence.py`, `frontend/src/types/api.ts`, tests  
**Scope**:
- Replace `VECTOR_STORE` contract usage with `PGVECTOR`
- Update any validation and serialization tests

### C.5 — Add ownership-aware data model fields and repository guards
**Applies to completed tasks**: 1.8, 3.x scaffolding  
**Files**: `backend/app/db/models.py`, `backend/app/db/repository.py`, migrations, route dependencies  
**Scope**:
- Add `user_id`, `guest_session_id`, and `is_guest` ownership markers
- Implement requester-scoped fetch/update methods
- Prevent cross-user and cross-session data access

### C.6 — Implement guest data deletion lifecycle
**Applies to completed tasks**: 3.x, 4.x scaffolding  
**Files**: backend cleanup endpoint/job, frontend session handling, tests  
**Scope**:
- Issue server-signed guest session credentials and require them for guest cleanup actions
- Delete guest data on explicit session end signal
- Add TTL-based cleanup as fallback for abandoned sessions
- Verify claims/evidence/timeline/history are removed for guest session

### C.7 — Add history capability for authenticated users only
**Applies to completed tasks**: 3.x, 4.x scaffolding  
**Files**: analysis/history endpoints, frontend history view components/hooks, tests  
**Scope**:
- Add authenticated history list endpoint and UI rendering
- Derive authenticated ownership from verified Supabase JWT (not client-supplied user-id header)
- Ensure guests cannot view or request historical analyses beyond active session
- Add unit and integration tests for both access modes

### C.8 — Harden Supabase JWT verification strategy (production-safe)
**Applies to completed tasks**: C.5, C.7
**Files**: `backend/app/api/dependencies.py`, auth config/docs, tests
**Scope**:
- Implement Supabase-compatible token verification supporting asymmetric/JWKS validation and strict claim checks (`exp`, `sub`, issuer/audience as configured)
- Keep shared-secret HS256 path only as an explicit development fallback
- Add negative tests for invalid signature, wrong issuer/audience, expired token

### C.9 — Normalize API field naming contract end-to-end
**Applies to completed tasks**: 1.4, 1.5, 1.6, 4.3, 4.4
**Files**: backend schemas/serializers, frontend API client/types, tests
**Scope**:
- Choose one canonical wire naming convention and codify it in backend responses and OpenAPI
- Remove mixed per-endpoint casing transformations
- Add contract tests to ensure analyze/poll/claims/evidence/timeline/compare all follow the same naming convention

### C.10 — Retrofit timeline and session schema fidelity
**Applies to completed tasks**: 1.8, 1.9, 6.1
**Files**: `backend/app/db/models.py`, migrations, `backend/db/schema.sql`, repository/tests
**Scope**:
- Add missing `chat_sessions` model/table and ownership linkage
- Store `analyses.timeline` as structured JSON/JSONB consistently across ORM, migrations, and SQL schema
- Align embedding schema types with production constraints (UUID FK for `evidence_embeddings.evidence_id`)

### C.11 — Align runtime defaults and config wiring with architecture
**Applies to completed tasks**: 1.1, 1.2, 1.6
**Files**: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/schemas/analysis.py`, tests
**Scope**:
- Ensure default analysis model is `gemini-3.1-flash-lite` across schema and runtime
- Wire CORS to `ALLOWED_ORIGINS` settings instead of hardcoded values
- Add regression tests for model default and CORS-config-driven behavior

**Planned file areas** (some already exist):
- `backend/app/schemas/` (5 files)
- `backend/app/agents/` (7 files: base, claim_extractor, retriever, verifier, critic, judge, workflow)
- `backend/app/db/` (4 files: models, session, vector_store, repository)
- `backend/app/api/routes/` (3 files: analysis, comparison, health)
- `backend/alembic/` (full Alembic setup)
- `backend/tests/` (conftest + integration tests)
- `frontend/src/types/`, `frontend/src/lib/`, `frontend/src/hooks/`, `frontend/src/components/`
- Docker, CI, and deployment files
