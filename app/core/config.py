from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sakhi AI API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://sakhi-ai-frontend-delta.vercel.app",
        ]
    )
    database_path: Path = Field(default_factory=lambda: Path(tempfile.gettempdir()) / "sakhi_ai.sqlite3")
    # AI provider: "rule-based" (default, no API key needed) or "openai"
    ai_provider_name: str = "rule-based"
    openai_api_key: SecretStr | None = Field(default=None)
    openai_model: str = "gpt-4o-mini"
    conversation_history_limit: int = 8
    secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-change-me"),
        validation_alias=AliasChoices("JWT_SECRET", "SAKHI_SECRET_KEY"),
    )
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    rate_limit_requests_per_minute: int = 60
    # Token blacklist backend: "memory" (default) or "redis"
    token_blacklist_backend: str = "memory"
    # Cache backend: "memory" (default) or "redis"
    cache_backend: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    redis_token_blacklist_prefix: str = "sakhi:token-blacklist"
    redis_cache_prefix: str = "sakhi:cache"
    cache_ttl_seconds: int = 300
    # Pagination defaults
    default_page_size: int = 20
    max_page_size: int = 100
    # Email settings
    email_backend: str = "console"        # "console" or "smtp"
    email_host: str = ""
    email_port: int = 587
    email_username: str = ""
    email_password: SecretStr = Field(default=SecretStr(""))
    email_from: str = "noreply@sakhiai.com"
    email_use_tls: bool = True

    model_config = SettingsConfigDict(
        env_prefix="SAKHI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return ["http://localhost:3000"]

    @field_validator("database_path", mode="before")
    @classmethod
    def parse_database_path(cls, value: object) -> Path:
        if value is None:
            return Path(tempfile.gettempdir()) / "sakhi_ai.sqlite3"
        if isinstance(value, Path):
            return value
        normalized = str(value).strip()
        if not normalized:
            return Path(tempfile.gettempdir()) / "sakhi_ai.sqlite3"
        return Path(normalized)

    @field_validator(
        "access_token_minutes",
        "refresh_token_days",
        "conversation_history_limit",
        "cache_ttl_seconds",
        "default_page_size",
        "max_page_size",
        mode="before",
    )
    @classmethod
    def parse_positive_int(cls, value: object) -> int:
        parsed_value = int(value)
        if parsed_value <= 0:
            raise ValueError("Numeric settings must be positive.")
        return parsed_value

    @model_validator(mode="after")
    def validate_runtime_settings(self) -> "Settings":
        normalized_environment = self.environment.strip().lower()
        normalized_provider = self.ai_provider_name.strip().lower()
        normalized_blacklist_backend = self.token_blacklist_backend.strip().lower()
        normalized_cache_backend = self.cache_backend.strip().lower()

        if normalized_environment in {"production", "staging"}:
            secret_key_value = self.secret_key.get_secret_value().strip()
            if not secret_key_value or secret_key_value == "dev-secret-change-me":
                raise ValueError(
                    "SAKHI_SECRET_KEY or JWT_SECRET must be configured before starting in production."
                )

        if (
            normalized_environment in {"production", "staging"}
            and normalized_provider == "openai"
            and self.openai_api_key is None
        ):
            raise ValueError("OPENAI_API_KEY must be configured when SAKHI_AI_PROVIDER_NAME is openai.")

        if normalized_blacklist_backend not in {"memory", "redis"}:
            raise ValueError("SAKHI_TOKEN_BLACKLIST_BACKEND must be either 'memory' or 'redis'.")

        if normalized_cache_backend not in {"memory", "redis"}:
            raise ValueError("SAKHI_CACHE_BACKEND must be either 'memory' or 'redis'.")

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

