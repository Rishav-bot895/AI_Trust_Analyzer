"""Tests for Alembic initial migration (Task 1.9)."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess[str]:
    """Run Alembic command with required env vars for settings validation."""
    env = os.environ.copy()
    env["GEMINI_API_KEY"] = "test-gemini-key"
    env["TAVILY_API_KEY"] = "test-tavily-key"
    env["DATABASE_URL"] = database_url
    env["SUPABASE_URL"] = "https://test-project.supabase.co"
    env["SUPABASE_ANON_KEY"] = "test-supabase-anon-key"
    env["SUPABASE_SERVICE_ROLE_KEY"] = "test-supabase-service-role-key"
    env["SUPABASE_JWT_SECRET"] = "test-supabase-jwt-secret"

    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _sqlite_tables(db_path: Path) -> set[str]:
    """Return all user-defined table names from a SQLite DB."""
    if not db_path.exists():
        return set()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {row[0] for row in rows}


def _sqlite_columns(db_path: Path, table: str) -> set[str]:
    """Return column names for a table from a SQLite DB."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_migration_upgrade_creates_tables(tmp_path: Path):
    """alembic upgrade head should create base and embedding tables."""
    db_path = tmp_path / "migration_upgrade.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    result = _run_alembic("upgrade", "head", database_url=database_url)
    assert result.returncode == 0, result.stdout + result.stderr

    tables = _sqlite_tables(db_path)
    assert {"analyses", "claims", "evidence", "evidence_embeddings"}.issubset(tables)

    analysis_columns = _sqlite_columns(db_path, "analyses")
    assert {"user_id", "guest_session_id", "is_guest"}.issubset(analysis_columns)


def test_migration_downgrade_removes_tables(tmp_path: Path):
    """alembic downgrade base should remove created tables and vector artifacts."""
    db_path = tmp_path / "migration_downgrade.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    upgrade_result = _run_alembic("upgrade", "head", database_url=database_url)
    assert upgrade_result.returncode == 0, upgrade_result.stdout + upgrade_result.stderr

    downgrade_result = _run_alembic("downgrade", "base", database_url=database_url)
    assert downgrade_result.returncode == 0, downgrade_result.stdout + downgrade_result.stderr

    tables = _sqlite_tables(db_path)
    assert "analyses" not in tables
    assert "claims" not in tables
    assert "evidence" not in tables
    assert "evidence_embeddings" not in tables


def test_pgvector_revision_contains_extension_and_drop_statements():
    """The pgvector revision should create and safely drop vector artifacts."""
    revision_path = BACKEND_ROOT / "alembic" / "versions" / "002_pgvector_embeddings.py"
    content = revision_path.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector" in content
    assert "CREATE TABLE IF NOT EXISTS evidence_embeddings" in content
    assert "DROP TABLE IF EXISTS evidence_embeddings" in content
    assert "DROP EXTENSION IF EXISTS vector" in content