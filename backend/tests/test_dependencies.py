from __future__ import annotations

import importlib
import subprocess
import sys


def test_all_imports_resolve():
    modules = [
        "langgraph",
        "langchain",
        "langchain_google_genai",
        "langchain_community",
        "tavily",
        "pgvector",
        "psycopg",
        "sentence_transformers",
        "sqlalchemy",
        "alembic",
        "pydantic_settings",
        "asyncpg",
        "supabase",
        "slowapi",
        "pytest",
        "pytest_asyncio",
        "httpx",
            "jwt",
    ]

    for module_name in modules:
        imported = importlib.import_module(module_name)
        assert imported is not None


def test_no_pip_conflicts():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
