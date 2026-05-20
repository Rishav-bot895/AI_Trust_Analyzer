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
    env["OPENAI_API_KEY"] = "test-openai-key"
    env["TAVILY_API_KEY"] = "test-tavily-key"
    env["DATABASE_URL"] = database_url

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


def test_migration_upgrade_creates_tables(tmp_path: Path):
    """alembic upgrade head should create analyses, claims, and evidence tables."""
    db_path = tmp_path / "migration_upgrade.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    result = _run_alembic("upgrade", "head", database_url=database_url)
    assert result.returncode == 0, result.stdout + result.stderr

    tables = _sqlite_tables(db_path)
    assert {"analyses", "claims", "evidence"}.issubset(tables)


def test_migration_downgrade_removes_tables(tmp_path: Path):
    """alembic downgrade base should remove created tables."""
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