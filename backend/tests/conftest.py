from __future__ import annotations

"""Shared pytest bootstrap and fixtures for backend tests.

Run tests with the project interpreter:
    .venv\\Scripts\\python.exe -m pytest
"""

import os
import sys
import tempfile
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

PYTEST_TMP = BACKEND_ROOT.parent / ".pytest_tmp"
PYTEST_TMP.mkdir(exist_ok=True)
os.environ.setdefault("TMP", str(PYTEST_TMP))
os.environ.setdefault("TEMP", str(PYTEST_TMP))
os.environ.setdefault("TMPDIR", str(PYTEST_TMP))
tempfile.tempdir = str(PYTEST_TMP)

# Shared defaults so importing app.core.config works across test modules.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-supabase-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-supabase-service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret-32bytes-long")
os.environ.setdefault("SUPABASE_JWT_VERIFY_STRATEGY", "hs256")


class FakeLLMResponse:
    """Minimal LangChain-like response object."""

    def __init__(self, content: str) -> None:
        self.content = content


class FakeLLM:
    """Deterministic fake model used to prevent real provider calls."""

    def __init__(self, content: str | None = None) -> None:
        self.content = content or (
            '{"claims":[{"text":"Apollo 11 landed on the Moon in 1969.",'
            '"confidence":0.95}]}'
        )
        self.calls: list[Any] = []

    def invoke(self, messages: Any) -> FakeLLMResponse:
        self.calls.append(messages)
        if not isinstance(messages, list):
            return FakeLLMResponse(self.content)

        system_prompt = ""
        user_prompt = ""
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            content = str(message.get("content") or "")
            if role == "system":
                system_prompt = content
            elif role == "user":
                user_prompt = content

        if "Extract only atomic factual claims" in system_prompt:
            return FakeLLMResponse(self.content)

        if "Classify each claim as SUPPORTED" in system_prompt:
            return FakeLLMResponse(
                '{"verdict":"SUPPORTED","confidence":0.93,'
                '"evidence_polarities":[{"evidence_index":0,"polarity":"FOR"}]}'
            )

        if "Analyze the full response for logical issues" in system_prompt:
            return FakeLLMResponse(
                '{"issues":[],"overall_assessment":"No logical issues detected."}'
            )

        if "Write clear decision-support summaries" in system_prompt:
            return FakeLLMResponse(
                "Most claims are supported by available evidence, with limited contradictory signals."
            )

        if "Rejected prior verdict" in user_prompt:
            return FakeLLMResponse(
                "Most claims are supported by available evidence, with limited contradictory signals."
            )

        return FakeLLMResponse(self.content)


class FakeTavilyClient:
    """Deterministic Tavily stand-in for retrieval tests."""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self.results = results or [
            {
                "title": "Apollo 11 - NASA",
                "url": "https://www.nasa.gov/mission/apollo-11/",
                "content": "NASA records Apollo 11 landing on the Moon in July 1969.",
                "score": 0.96,
            }
        ]
        self.queries: list[dict[str, Any]] = []

    def search(self, query: str, max_results: int = 3) -> dict[str, Any]:
        self.queries.append({"query": query, "max_results": max_results})
        return {"results": self.results[:max_results]}


@pytest.fixture
def test_database_url(tmp_path: Path) -> str:
    """Return a PostgreSQL test URL when configured, otherwise an isolated SQLite DB."""
    configured = os.getenv("TEST_DATABASE_URL")
    if configured:
        return configured
    return f"sqlite+aiosqlite:///{(tmp_path / 'pytest.db').as_posix()}"


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Generator[None, None, None]:
    """Keep SlowAPI's in-memory counters isolated per test."""
    from app.api.middleware import limiter

    limiter.limiter.storage.reset()
    try:
        yield
    finally:
        limiter.limiter.storage.reset()


@pytest_asyncio.fixture
async def test_db_engine(
    test_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[AsyncEngine, None]:
    """Create the test schema and expose an async SQLAlchemy engine."""
    from app.core.config import settings
    from app.db.models import Base

    monkeypatch.setattr(settings, "DATABASE_URL", test_database_url)
    engine = create_async_engine(test_database_url, future=True)

    async with engine.begin() as conn:
        if test_database_url.startswith("postgresql"):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a clean async DB session for repository and API integration tests."""
    session_factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_llm() -> Generator[FakeLLM, None, None]:
    """Patch all agent LLM factories with a deterministic fake model."""
    fake = FakeLLM()

    with (
        patch("app.agents.base.get_llm", return_value=fake),
        patch("app.agents.claim_extractor.get_llm", return_value=fake),
        patch("app.agents.verifier.get_llm", return_value=fake),
        patch("app.agents.critic.get_llm", return_value=fake),
        patch("app.agents.judge.get_llm", return_value=fake),
    ):
        yield fake


@pytest.fixture
def mock_tavily_client() -> Generator[FakeTavilyClient, None, None]:
    """Patch Tavily retrieval with deterministic search results."""
    fake = FakeTavilyClient()
    with patch("app.agents.retriever._get_tavily_client", return_value=fake):
        yield fake


@pytest.fixture
def authenticated_jwt() -> str:
    """Return a valid HS256 Supabase-style JWT for tests."""
    return jwt.encode(
        {
            "sub": "test-user-id",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        os.environ["SUPABASE_JWT_SECRET"],
        algorithm="HS256",
    )


@pytest.fixture
def auth_headers(authenticated_jwt: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {authenticated_jwt}"}


@pytest.fixture
def guest_session_id() -> str:
    return str(uuid4())


@pytest.fixture
def guest_headers(guest_session_id: str) -> dict[str, str]:
    from app.api.dependencies import create_guest_session_token

    return {
        "X-Guest-Session-Id": guest_session_id,
        "X-Guest-Session-Token": create_guest_session_token(guest_session_id),
    }


@pytest_asyncio.fixture
async def async_client(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    """Yield an HTTPX async client wired to the FastAPI app and test DB."""
    from app.api.routes import analysis as analysis_routes
    from app.api.routes import guest as guest_routes
    from app.main import app

    session_factory = async_sessionmaker(test_db_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[analysis_routes.get_db] = override_get_db
    app.dependency_overrides[guest_routes.get_db] = override_get_db
    original_background_session_factory = analysis_routes.AsyncSessionLocal
    analysis_routes.AsyncSessionLocal = session_factory

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        analysis_routes.AsyncSessionLocal = original_background_session_factory
        app.dependency_overrides.clear()
