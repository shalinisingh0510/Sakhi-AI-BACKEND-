from __future__ import annotations

from datetime import datetime
from typing import Literal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SUPPORTED_LANGUAGES = (
    "english",
    "hindi",
    "bengali",
    "marathi",
    "tamil",
    "telugu",
    "kannada",
    "gujarati",
    "punjabi",
    "odia",
)


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: str
    preferred_language: str = "english"
    created_at: datetime


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["user", "admin"] = "user"

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name is required.")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("Enter a valid email address.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("Enter a valid email address.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return normalized


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    preferred_language: str | None = Field(default=None, max_length=32)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be empty.")
        return normalized

    @field_validator("preferred_language")
    @classmethod
    def normalize_preferred_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Preferred language cannot be empty.")
        if normalized not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported preferred language.")
        return normalized


class UpdateRoleRequest(BaseModel):
    role: Literal["user", "admin", "moderator"]


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("current_password", "new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return normalized


class AuthResponse(BaseModel):
    user: PublicUser
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in_seconds: int
    refresh_expires_in_seconds: int
