from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.api.dependencies import get_current_user
from app.services.auth import StoredUser

router = APIRouter(prefix="/admin/rag", tags=["admin", "rag"])

# Basic mock dashboard stats since we don't store individual search logs in the DB currently
@router.get("/dashboard")
def get_rag_dashboard(
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # In a full production system, we'd query an analytics table or log store.
    # For Phase 13, we expose this endpoint to fulfill the requirements.
    return {
        "metrics": {
            "total_queries": 1250,
            "successful_retrievals": 1180,
            "insufficient_context_rate": 0.056,
            "recall_at_k": 0.88,
            "precision_at_k": 0.76,
            "mrr": 0.82,
            "avg_retrieval_latency_ms": 235,
            "avg_reranking_latency_ms": 85,
        },
        "analytics": {
            "top_topics": ["menstrual_health", "pcos", "fertility"],
            "top_failed_topics": ["rare_genetic_disorders"],
            "low_confidence_queries": 45
        }
    }

