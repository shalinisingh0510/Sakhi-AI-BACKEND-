from __future__ import annotations

import re
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.schemas.auth import SUPPORTED_LANGUAGES

CONVERSATION_ID_PATTERN = re.compile(r'^[0-9a-f]{32}$')


class ChatMessageRequest(BaseModel):
    conversation_id: str | None = Field(
        default=None,
        max_length=32,
        validation_alias=AliasChoices('conversation_id', 'conversationId'),
    )
    message: str = Field(min_length=1, max_length=4000)
    preferred_language: str | None = Field(
        default=None,
        max_length=32,
        validation_alias=AliasChoices('preferred_language', 'preferredLanguage'),
    )
    mode: Literal['text', 'voice'] = 'text'

    @field_validator('conversation_id')
    @classmethod
    def normalize_conversation_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError('Conversation ID cannot be empty.')
        if not CONVERSATION_ID_PATTERN.fullmatch(normalized):
            raise ValueError('Conversation ID must be a 32-character hexadecimal string.')
        return normalized

    @field_validator('message')
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('Message is required.')
        return normalized

    @field_validator('preferred_language')
    @classmethod
    def normalize_preferred_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError('Preferred language cannot be empty.')
        if normalized not in SUPPORTED_LANGUAGES:
            raise ValueError('Unsupported preferred language.')
        return normalized
