"""Tests for SQLAlchemy models and DB session dependency (Task 1.8)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Analysis, Claim


def _reload_session_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Reload session module with controlled environment variables."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test_task_1_8.db")
    sys.modules.pop("app.core.config", None)
    sys.modules.pop("app.db.session", None)
    return importlib.import_module("app.db.session")


def test_analysis_model_table_name():
    """Analysis model should map to analyses table."""
    assert Analysis.__tablename__ == "analyses"


def test_claim_fk_to_analysis():
    """Claim model should include foreign key to analyses.id."""
    fk_targets = {fk.target_fullname for fk in Claim.__table__.c.analysis_id.foreign_keys}
    assert "analyses.id" in fk_targets


@pytest.mark.asyncio
async def test_get_db_yields_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """get_db should yield an AsyncSession instance."""
    session_module = _reload_session_module(monkeypatch, tmp_path)

    gen = session_module.get_db()
    session = await anext(gen)

    assert isinstance(session, AsyncSession)

    await gen.aclose()


@pytest.mark.asyncio
async def test_get_db_closes_on_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """get_db should close the session when generator exits."""
    session_module = _reload_session_module(monkeypatch, tmp_path)

    gen = session_module.get_db()
    session = await anext(gen)

    close_spy = AsyncMock(wraps=session.close)
    session.close = close_spy

    with pytest.raises(StopAsyncIteration):
        await anext(gen)

    close_spy.assert_awaited_once()