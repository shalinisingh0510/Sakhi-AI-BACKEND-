from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service, require_roles
from app.schemas.auth import PublicUser, UpdateRoleRequest
from app.services.auth import AuthService, InvalidRoleError, StoredUser, UserNotFoundError

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
def admin_overview(current_user: StoredUser = Depends(require_roles("admin"))) -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Admin access granted",
        "user": current_user.email,
    }


@router.get("/users", response_model=list[PublicUser])
def list_users(
    _current_user: StoredUser = Depends(require_roles("admin")),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[PublicUser]:
    return [user.to_public_user() for user in auth_service.list_users()]


@router.patch("/users/{user_id}/role", response_model=PublicUser)
def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    _current_user: StoredUser = Depends(require_roles("admin")),
    auth_service: AuthService = Depends(get_auth_service),
) -> PublicUser:
    try:
        user = auth_service.update_user_role(user_id=user_id, role=payload.role)
    except InvalidRoleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return user.to_public_user()
