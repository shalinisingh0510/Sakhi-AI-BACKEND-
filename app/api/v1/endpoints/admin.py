from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import require_roles
from app.services.auth import StoredUser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
def admin_overview(current_user: StoredUser = Depends(require_roles("admin"))) -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Admin access granted",
        "user": current_user.email,
    }
