from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sakhi AI API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    secret_key: SecretStr = Field(default=SecretStr("dev-secret-change-me"))
    access_token_minutes: int = 60
    refresh_token_days: int = 7

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

    @field_validator("access_token_minutes", "refresh_token_days", mode="before")
    @classmethod
    def parse_positive_int(cls, value: object) -> int:
        parsed_value = int(value)
        if parsed_value <= 0:
            raise ValueError("Token lifetimes must be positive.")
        return parsed_value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
