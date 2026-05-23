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
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("SUPABASE_JWT_VERIFY_STRATEGY", "hs256")
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", "https://issuer.example")
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "audience-example")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.setenv("ALLOWED_ORIGINS", "[\"http://localhost:3000\", \"http://localhost:5173\"]")

    config = _reload_config_module(monkeypatch, tmp_path)

    assert config.settings.GEMINI_API_KEY == "test-gemini-key"
    assert config.settings.TAVILY_API_KEY == "test-tavily-key"
    assert config.settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
    assert config.settings.SUPABASE_URL == "https://example.supabase.co"
    assert config.settings.SUPABASE_ANON_KEY == "anon-key"
    assert config.settings.SUPABASE_SERVICE_ROLE_KEY == "service-role-key"
    assert config.settings.SUPABASE_JWT_SECRET == "jwt-secret"
    assert config.settings.SUPABASE_JWT_VERIFY_STRATEGY == "hs256"
    assert config.settings.SUPABASE_JWT_ISSUER == "https://issuer.example"
    assert config.settings.SUPABASE_JWT_AUDIENCE == "audience-example"
    assert config.settings.SUPABASE_JWKS_URL == "https://issuer.example/.well-known/jwks.json"
    assert config.settings.ALLOWED_ORIGINS == ["http://localhost:3000", "http://localhost:5173"]


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")

    with pytest.raises(ValidationError):
        _reload_config_module(monkeypatch, tmp_path)


def test_default_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
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
        "GEMINI_API_KEY",
        "TAVILY_API_KEY",
        "DATABASE_URL",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_JWT_SECRET",
        "SUPABASE_JWT_VERIFY_STRATEGY",
        "SUPABASE_JWT_ISSUER",
        "SUPABASE_JWT_AUDIENCE",
        "SUPABASE_JWKS_URL",
        "ENVIRONMENT",
        "ALLOWED_ORIGINS",
        "LOG_LEVEL",
        "MAX_CLAIMS",
        "VECTOR_EMBEDDING_DIM",
        "GUEST_SESSION_TTL_HOURS",
    }
    assert expected.issubset(keys)


def test_resolve_supabase_jwks_url_from_supabase_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)

    config = _reload_config_module(monkeypatch, tmp_path)

    assert (
        config.resolve_supabase_jwks_url()
        == "https://example.supabase.co/auth/v1/.well-known/jwks.json"
    )
