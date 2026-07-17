from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_ai_service, get_current_user, pagination_params
from app.schemas.ai import ConversationDetail, ConversationSummary, CreateConversationRequest, SendMessageRequest
from app.services.ai import AIService, ConversationNotFoundError
from app.services.auth import StoredUser

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service),
) -> list[ConversationSummary]:
    offset, limit = pagination
    all_conversations = ai_service.list_conversations(user_id=current_user.id)
    return all_conversations[offset : offset + limit]


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: CreateConversationRequest,
    current_user: StoredUser = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service),
) -> ConversationDetail:
    return ai_service.create_conversation(
        user_id=current_user.id,
        title=payload.title,
        initial_message=payload.initial_message,
        preferred_language=payload.preferred_language,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    current_user: StoredUser = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service),
) -> ConversationDetail:
    try:
        return ai_service.get_conversation(user_id=current_user.id, conversation_id=conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{conversation_id}/messages", response_model=ConversationDetail)
def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    current_user: StoredUser = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service),
) -> ConversationDetail:
    try:
        return ai_service.send_message(user_id=current_user.id, conversation_id=conversation_id, message=payload.message)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
