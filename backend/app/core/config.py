from __future__ import annotations

import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	GEMINI_API_KEY: str
	TAVILY_API_KEY: str
	DATABASE_URL: str
	CHROMA_PERSIST_DIR: str = "./data/chroma"
	ENVIRONMENT: str = "development"
	ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
	LOG_LEVEL: str = "INFO"
	MAX_CLAIMS: int = 50

	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

	@field_validator("GEMINI_API_KEY")
	@classmethod
	def validate_gemini_api_key(cls, value: str) -> str:
		if not value or not value.strip():
			raise ValueError("GEMINI_API_KEY must be a non-empty string")
		return value

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


settings = Settings()
