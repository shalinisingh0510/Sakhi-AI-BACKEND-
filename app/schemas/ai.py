from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import SUPPORTED_LANGUAGES


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    preferred_language: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationDetail(BaseModel):
    conversation: ConversationSummary
    messages: list[ConversationMessage]


class CreateConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    initial_message: str = Field(min_length=1, max_length=4000)
    preferred_language: str | None = Field(default=None, max_length=32)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("initial_message")
    @classmethod
    def normalize_initial_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Initial message is required.")
        return normalized

    @field_validator("preferred_language")
    @classmethod
    def normalize_preferred_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported preferred language.")
        return normalized


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message is required.")
        return normalized
