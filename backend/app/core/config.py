from __future__ import annotations

import json
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	GEMINI_API_KEY: str
	TAVILY_API_KEY: str
	ENVIRONMENT: str = "development"
	DATABASE_URL: str
	SUPABASE_URL: str
	SUPABASE_ANON_KEY: str
	SUPABASE_SERVICE_ROLE_KEY: str
	SUPABASE_JWT_SECRET: str
	SUPABASE_JWT_VERIFY_STRATEGY: str = "jwks"
	SUPABASE_JWT_ISSUER: str | None = None
	SUPABASE_JWT_AUDIENCE: str | None = None
	SUPABASE_JWKS_URL: str | None = None
	ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
	LOG_LEVEL: str = "INFO"
	MAX_CLAIMS: int = 50
	VECTOR_EMBEDDING_DIM: int = 384
	GUEST_SESSION_TTL_HOURS: int = 24

	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

	@field_validator(
		"GEMINI_API_KEY",
		"TAVILY_API_KEY",
		"DATABASE_URL",
		"SUPABASE_URL",
		"SUPABASE_ANON_KEY",
		"SUPABASE_SERVICE_ROLE_KEY",
		"SUPABASE_JWT_SECRET",
	)
	@classmethod
	def validate_non_empty_str(cls, value: str) -> str:
		if not value or not value.strip():
			raise ValueError("Setting must be a non-empty string")
		return value

	@field_validator("MAX_CLAIMS", "VECTOR_EMBEDDING_DIM", "GUEST_SESSION_TTL_HOURS")
	@classmethod
	def validate_positive_int(cls, value: int) -> int:
		if value <= 0:
			raise ValueError("Setting must be a positive integer")
		return value

	@field_validator("SUPABASE_JWT_VERIFY_STRATEGY")
	@classmethod
	def validate_jwt_verify_strategy(cls, value: str) -> str:
		normalized = value.strip().lower()
		if normalized not in {"jwks", "hs256"}:
			raise ValueError("SUPABASE_JWT_VERIFY_STRATEGY must be 'jwks' or 'hs256'")
		return normalized

	@field_validator("SUPABASE_JWT_ISSUER", "SUPABASE_JWT_AUDIENCE", "SUPABASE_JWKS_URL", mode="before")
	@classmethod
	def normalize_optional_str(cls, value: Any) -> str | None:
		if value is None:
			return None
		raw = str(value).strip()
		return raw or None

	@field_validator("ALLOWED_ORIGINS", mode="before")
	@classmethod
	def parse_allowed_origins(cls, value: Any) -> list[str]:
		if value is None:
			return ["http://localhost:3000"]

		if isinstance(value, list):
			return [str(item).strip() for item in value if str(item).strip()]

		if isinstance(value, str):
			raw = value.strip()
			if not raw:
				return ["http://localhost:3000"]

			# Support both JSON array strings and comma-separated values.
			if raw.startswith("["):
				parsed = json.loads(raw)
				if not isinstance(parsed, list):
					raise ValueError("ALLOWED_ORIGINS JSON value must be an array")
				return [str(item).strip() for item in parsed if str(item).strip()]

			return [item.strip() for item in raw.split(",") if item.strip()]

		raise ValueError("ALLOWED_ORIGINS must be a list or string")

	@model_validator(mode="after")
	def validate_database_url_for_runtime(self) -> Settings:
		"""Require asyncpg runtime URL in development/production environments."""
		if self.ENVIRONMENT in {"development", "production"}:
			if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
				raise ValueError(
					"DATABASE_URL must use postgresql+asyncpg:// in development and production"
				)
		return self


settings = Settings()


def resolve_supabase_jwks_url() -> str:
	"""Resolve JWKS URL from explicit config or Supabase project URL."""
	if settings.SUPABASE_JWKS_URL:
		return settings.SUPABASE_JWKS_URL
	return settings.SUPABASE_URL.rstrip("/") + "/auth/v1/.well-known/jwks.json"
