from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_chat_service, get_current_user
from app.schemas.ai import ConversationDetail
from app.schemas.chat import ChatMessageRequest
from app.services.ai import ConversationNotFoundError
from app.services.auth import StoredUser
from app.services.chat import ChatService

router = APIRouter(prefix='/chat', tags=['chat'])


@router.post('/message', response_model=ConversationDetail)
def send_chat_message(
    payload: ChatMessageRequest,
    current_user: StoredUser = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationDetail:
    try:
        preferred_language = payload.preferred_language or current_user.preferred_language
        return chat_service.send_message(
            user_id=current_user.id,
            message=payload.message,
            conversation_id=payload.conversation_id,
            preferred_language=preferred_language,
            mode=payload.mode,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
