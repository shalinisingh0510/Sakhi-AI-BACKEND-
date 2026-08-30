from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_ai_service, get_current_user
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.ai import AIService, ConversationNotFoundError
from app.services.auth import StoredUser

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
    ai_service: AIService = Depends(get_ai_service),
) -> ChatMessageResponse:
    try:
        preferred_language = payload.preferred_language or current_user.preferred_language
        
        # 1. Intent Routing
        from app.services.ai_orchestration.intent import IntentRouter, IntentCategory
        intent_result = IntentRouter().route(payload.message)
        
        # 2. Gather Personal Health Context
        health_context_dict = None
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            # We always add "PROFILE" scope to ensure 'age' is calculated for safety routing
            scopes = set(intent_result.required_scopes)
            scopes.add("PROFILE")
            
            from app.services.ai_context.context_builder import HealthContextBuilder
            context_obj = HealthContextBuilder(db, current_user.id).build_context(list(scopes))
            if context_obj:
                health_context_dict = context_obj.model_dump()
            
            # If personalization is disabled, context_obj is None. We still need age for safety!
            if not health_context_dict:
                from app.models.health_profile import HealthProfile
                import datetime
                profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
                if profile and profile.date_of_birth:
                    today = datetime.date.today()
                    age = today.year - profile.date_of_birth.year - ((today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))
                    health_context_dict = {"age": age}
        finally:
            db.close()
            
        if payload.conversation_id:
            detail = ai_service.send_message(
                user_id=current_user.id,
                conversation_id=payload.conversation_id,
                message=payload.message,
                mode=payload.mode,
                health_context=health_context_dict,
            )
        else:
            detail = ai_service.create_conversation(
                user_id=current_user.id,
                title=None,
                initial_message=payload.message,
                preferred_language=preferred_language,
                mode=payload.mode,
                health_context=health_context_dict,
            )
            
        assistant_message = detail.messages[-1] if detail.messages else None
        if assistant_message is None:
            raise RuntimeError("Assistant message was not stored.")

        from app.schemas.chat import ChatMessageContent, ChatMessageData
        return ChatMessageResponse(
            success=True,
            data=ChatMessageData(
                conversation_id=detail.conversation.id,
                message=ChatMessageContent.model_validate(assistant_message),
            ),
            conversation=detail.conversation,
            messages=detail.messages,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc