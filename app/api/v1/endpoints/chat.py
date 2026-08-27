from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_chat_service, get_current_user
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.ai import ConversationNotFoundError
from app.services.auth import StoredUser
from app.services.chat import ChatService

router = APIRouter(tags=["Chat"])


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a chat message and receive an assistant response",
)
@router.post(
    "",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def send_chat_message(
    payload: ChatMessageRequest,
    current_user: StoredUser = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    try:
        data = chat_service.process_chat_message(
            user_id=current_user.id,
            message=payload.message,
            conversation_id=payload.conversation_id,
            language=payload.language,
        )
        return ChatMessageResponse(success=True, data=data)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
