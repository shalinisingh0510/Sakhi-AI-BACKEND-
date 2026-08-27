from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000, description="User chat message")
    conversation_id: str | None = Field(
        default=None,
        alias="conversationId",
        max_length=64,
        description="Optional existing conversation ID",
    )
    language: str | None = Field(
        default=None,
        max_length=32,
        description="Optional preferred language for the response",
    )

    model_config = ConfigDict(populate_by_name=True)

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
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None


class ChatMessageContent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: Literal["assistant", "user"] = "assistant"
    content: str
    created_at: datetime


class ChatMessageData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: str
    conversationId: str
    message: ChatMessageContent


class ChatMessageResponse(BaseModel):
    success: bool = True
    data: ChatMessageData
