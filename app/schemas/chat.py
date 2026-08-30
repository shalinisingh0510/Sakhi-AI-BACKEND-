from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.ai import ConversationMessage, ConversationSummary
from app.schemas.auth import SUPPORTED_LANGUAGES

CONVERSATION_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000, description="User chat message")
    conversation_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional existing conversation ID",
        validation_alias=AliasChoices("conversation_id", "conversationId"),
    )
    preferred_language: str | None = Field(
        default=None,
        max_length=32,
        description="Optional preferred language for the response",
        validation_alias=AliasChoices("preferred_language", "preferredLanguage", "language"),
    )
    mode: Literal["text", "voice"] = "text"

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def validate_raw_conversation_id(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        if "conversation_id" in data:
            raw_value = data.get("conversation_id")
            if raw_value is None:
                return data
            normalized = str(raw_value).strip().lower()
            if not normalized:
                raise ValueError("Conversation ID cannot be empty.")
            if not CONVERSATION_ID_PATTERN.fullmatch(normalized):
                raise ValueError("Conversation ID must be a 32-character hexadecimal string.")

        if "conversationId" in data:
            raw_value = data.get("conversationId")
            if raw_value is None:
                return data
            normalized = str(raw_value).strip()
            if not normalized:
                raise ValueError("Conversation ID cannot be empty.")

        return data

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Message must be a string.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message cannot be empty or contain only whitespace.")
        return normalized

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("preferred_language")
    @classmethod
    def validate_preferred_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Preferred language cannot be empty.")
        if normalized not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported preferred language.")
        return normalized


class ChatMessageContent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: Literal["assistant", "user"] = "assistant"
    content: str
    citations: list[dict] | None = None
    created_at: datetime


class ChatMessageData(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    conversation_id: str = Field(alias="conversationId")
    message: ChatMessageContent


class ChatMessageResponse(BaseModel):
    success: bool = True
    data: ChatMessageData
    conversation: ConversationSummary
    messages: list[ConversationMessage]