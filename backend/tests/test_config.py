from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


def _reload_config_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    # Ensure .env is not implicitly loaded from project directories during this test.
    monkeypatch.chdir(tmp_path)
    sys.modules.pop("app.core.config", None)
    return importlib.import_module("app.core.config")


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
    monkeypatch.setenv("ALLOWED_ORIGINS", "[\"http://localhost:3000\", \"http://localhost:5173\"]")

    config = _reload_config_module(monkeypatch, tmp_path)

    assert config.settings.OPENAI_API_KEY == "test-openai-key"
    assert config.settings.TAVILY_API_KEY == "test-tavily-key"
    assert config.settings.DATABASE_URL == "sqlite+aiosqlite:///./dev.db"
    assert config.settings.ALLOWED_ORIGINS == ["http://localhost:3000", "http://localhost:5173"]


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")

    with pytest.raises(ValidationError):
        _reload_config_module(monkeypatch, tmp_path)


def test_default_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    config = _reload_config_module(monkeypatch, tmp_path)

    assert config.settings.ENVIRONMENT == "development"


def test_env_example_contains_all_keys():
    env_example_path = Path(__file__).resolve().parents[1] / ".env.example"
    content = env_example_path.read_text(encoding="utf-8")

    keys = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.add(line.split("=", 1)[0].strip())

    expected = {
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
        "DATABASE_URL",
        "CHROMA_PERSIST_DIR",
        "ENVIRONMENT",
        "ALLOWED_ORIGINS",
        "LOG_LEVEL",
        "MAX_CLAIMS",
    }
    assert expected.issubset(keys)
