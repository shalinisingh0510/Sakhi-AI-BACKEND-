from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.services.auth import StoredUser
from app.models.integrations import HealthProviderConnection, ExternalSyncLog, ProviderType, ConnectionStatus, SyncStatus
from app.services.integrations.google_fit import GoogleFitAdapter
from app.services.integrations.normalizer import IntegrationNormalizer

router = APIRouter(prefix="/integrations", tags=["integrations"])

class ConnectRequest(BaseModel):
    provider: ProviderType
    auth_code: str

class SyncResponse(BaseModel):
    status: str
    imported: int
    updated: int
    skipped: int

@router.post("/connect", response_model=Dict[str, Any])
def connect_provider(
    payload: ConnectRequest,
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect a health provider (e.g. Google Fit).
    """
    if payload.provider != ProviderType.GOOGLE_HEALTH_CONNECT:
        raise HTTPException(status_code=400, detail="Only Google Fit is supported in this demo.")
        
    adapter = GoogleFitAdapter()
    token_data = adapter.authenticate(payload.auth_code)
    
    # Check if already connected
    conn = db.query(HealthProviderConnection).filter(
        HealthProviderConnection.user_id == current_user.id,
        HealthProviderConnection.provider == payload.provider
    ).first()
    
    if not conn:
        conn = HealthProviderConnection(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            provider=payload.provider,
            status=ConnectionStatus.CONNECTED,
            scopes=["ACTIVITY", "STEPS"],
            provider_user_id=token_data.get("provider_user_id")
        )
        db.add(conn)
    else:
        conn.status = ConnectionStatus.CONNECTED
        conn.provider_user_id = token_data.get("provider_user_id")
        
    db.commit()
    
    return {"status": "success", "connection_id": conn.id}

@router.post("/sync", response_model=SyncResponse)
def trigger_sync(
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manual trigger to pull recent data from connected providers.
    In production, this is handled by a Celery background task.
    """
    connections = db.query(HealthProviderConnection).filter(
        HealthProviderConnection.user_id == current_user.id,
        HealthProviderConnection.status == ConnectionStatus.CONNECTED
    ).all()
    
    if not connections:
        raise HTTPException(status_code=400, detail="No active integrations found.")
        
    total_imported, total_updated, total_skipped = 0, 0, 0
    
    for conn in connections:
        if conn.provider == ProviderType.GOOGLE_HEALTH_CONNECT:
            adapter = GoogleFitAdapter()
            # Fetch last 7 days for demo
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            
            # Start sync log
            sync_log = ExternalSyncLog(
                id=str(uuid.uuid4()),
                connection_id=conn.id,
                status=SyncStatus.PARTIAL # update to success later
            )
            db.add(sync_log)
            db.commit()
            
            try:
                # Fetch
                records = adapter.fetch_activities(token_data={}, start_date=start_date, end_date=end_date)
                
                # Normalize & Store
                normalizer = IntegrationNormalizer(db)
                imp, upd, skip = normalizer.sync_activities(current_user.id, conn.provider.value, records)
                
                total_imported += imp
                total_updated += upd
                total_skipped += skip
                
                sync_log.status = SyncStatus.SUCCESS
                sync_log.records_imported = imp
                sync_log.records_updated = upd
                sync_log.records_skipped = skip
                sync_log.sync_completed_at = datetime.utcnow()
                
                conn.last_sync_at = datetime.utcnow()
                
            except Exception as e:
                sync_log.status = SyncStatus.FAILED
                sync_log.error_message = str(e)
                sync_log.sync_completed_at = datetime.utcnow()
                
            db.commit()
            
    return SyncResponse(
        status="success",
        imported=total_imported,
        updated=total_updated,
        skipped=total_skipped
    )
