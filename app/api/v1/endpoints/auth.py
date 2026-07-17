from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service, get_current_user
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    PublicUser,
    RefreshRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from app.services.auth import (
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidProfileUpdateError,
    InvalidRoleError,
    InvalidTokenError,
    StoredUser,
    UserNotFoundError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_to_response(session) -> AuthResponse:
    return AuthResponse(
        user=session.user.to_public_user(),
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        token_type=session.token_type,
        expires_in_seconds=session.expires_in_seconds,
        refresh_expires_in_seconds=session.refresh_expires_in_seconds,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        session = auth_service.register_user(
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=payload.role,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidRoleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _session_to_response(session)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        session = auth_service.login_user(email=payload.email, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return _session_to_response(session)


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        session = auth_service.refresh_session(refresh_token=payload.refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return _session_to_response(session)


@router.get("/me", response_model=PublicUser)
def me(current_user: StoredUser = Depends(get_current_user)) -> PublicUser:
    return current_user.to_public_user()


@router.patch("/me", response_model=PublicUser)
def update_me(
    payload: UpdateProfileRequest,
    current_user: StoredUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> PublicUser:
    try:
        user = auth_service.update_profile(
            user_id=current_user.id,
            name=payload.name,
            preferred_language=payload.preferred_language,
        )
    except InvalidProfileUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return user.to_public_user()


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: StoredUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Change the authenticated user's password. Returns 204 on success."""
    try:
        auth_service.change_password(
            user_id=current_user.id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except InvalidProfileUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
