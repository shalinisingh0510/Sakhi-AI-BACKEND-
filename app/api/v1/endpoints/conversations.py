from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session

from app.api.dependencies import get_ai_service, get_current_user, pagination_params
from app.db.dependencies import get_db
from app.schemas.ai import ConversationDetail, ConversationSummary, CreateConversationRequest, SendMessageRequest
from app.services.ai import AIService, ConversationNotFoundError
from app.services.auth import StoredUser
from app.services.ai_context.context_builder import HealthContextBuilder
from app.services.ai_orchestration.intent import IntentRouter, IntentCategory
from app.services.ai_orchestration.safety import HealthSafetyRouter, HealthAIResponseGuard, SafetyRiskLevel
from app.services.rag.retrieval import MedicalKnowledgeService
from app.models.health_profile import HealthProfile

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
    db: Session = Depends(get_db),
) -> ConversationDetail:
    intent_result = IntentRouter().route(payload.initial_message)
    scopes = intent_result.required_scopes
    
    context_obj = HealthContextBuilder(db, current_user.id).build_context(scopes)
    health_context_dict = context_obj.model_dump() if context_obj else None

    return ai_service.create_conversation(
        user_id=current_user.id,
        title=payload.title,
        initial_message=payload.initial_message,
        preferred_language=payload.preferred_language,
        mode=payload.mode,
        health_context=health_context_dict,
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
    db: Session = Depends(get_db),
) -> ConversationDetail:
    # 1. Intent Routing
    intent_result = IntentRouter().route(payload.message)
    
    # 2. Gather Personal Health Context
    health_context_dict = None
    if intent_result.category in (IntentCategory.PERSONAL_HEALTH, IntentCategory.COMBINED):
        context_obj = HealthContextBuilder(db, current_user.id).build_context(intent_result.required_scopes)
        if context_obj:
            health_context_dict = context_obj.model_dump()
            
    # Include age directly in health context for safety checks
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if profile and profile.date_of_birth:
        import datetime
        today = datetime.date.today()
        age = today.year - profile.date_of_birth.year - ((today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))
        if health_context_dict:
            health_context_dict["age"] = age
        else:
            health_context_dict = {"age": age}

    # 3. Generate Response via AIService (handles Safety, RAG, and LLM)
    try:
        return ai_service.send_message(
            user_id=current_user.id,
            conversation_id=conversation_id,
            message=payload.message,
            mode=payload.mode,
            health_context=health_context_dict,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
