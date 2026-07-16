from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.core.config import Settings
from app.core.security import build_token_claims, decode_token, encode_token, hash_password, verify_password
from app.schemas.auth import PublicUser


class AuthError(Exception):
    """Base exception for authentication and authorization failures."""


class DuplicateEmailError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InvalidTokenError(AuthError):
    pass


class InvalidRoleError(AuthError):
    pass


@dataclass(slots=True)
class StoredUser:
    id: str
    name: str
    email: str
    password_hash: str
    role: str
    created_at: datetime

    def to_public_user(self) -> PublicUser:
        return PublicUser.model_validate(self)


class AuthStoreProtocol(Protocol):
    def create_user(self, *, name: str, email: str, password: str, role: str) -> StoredUser:
        ...

    def get_by_email(self, email: str) -> StoredUser | None:
        ...

    def get_by_id(self, user_id: str) -> StoredUser | None:
        ...

    def authenticate(self, *, email: str, password: str) -> StoredUser:
        ...


@dataclass(slots=True)
class AuthSession:
    user: StoredUser
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 0
    refresh_expires_in_seconds: int = 0


class InMemoryAuthStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._users_by_id: dict[str, StoredUser] = {}
        self._users_by_email: dict[str, StoredUser] = {}

    def create_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        role: str,
    ) -> StoredUser:
        normalized_email = email.strip().lower()
        normalized_role = role.strip().lower()

        with self._lock:
            if normalized_email in self._users_by_email:
                raise DuplicateEmailError("An account already exists for this email.")

            user = StoredUser(
                id=uuid4().hex,
                name=name.strip(),
                email=normalized_email,
                password_hash=hash_password(password),
                role=normalized_role,
                created_at=datetime.now(timezone.utc),
            )
            self._users_by_id[user.id] = user
            self._users_by_email[normalized_email] = user
            return user

    def get_by_email(self, email: str) -> StoredUser | None:
        return self._users_by_email.get(email.strip().lower())

    def get_by_id(self, user_id: str) -> StoredUser | None:
        return self._users_by_id.get(user_id)

    def authenticate(self, *, email: str, password: str) -> StoredUser:
        user = self.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        return user


class AuthService:
    def __init__(self, settings: Settings, store: AuthStoreProtocol | None = None) -> None:
        self._settings = settings
        self._store = store or InMemoryAuthStore()

    @property
    def secret_key(self) -> str:
        return self._settings.secret_key.get_secret_value()

    def register_user(self, *, name: str, email: str, password: str, role: str = "user") -> AuthSession:
        normalized_role = role.strip().lower()
        if normalized_role not in {"user", "admin"}:
            raise InvalidRoleError("Unsupported user role.")

        user = self._store.create_user(name=name, email=email, password=password, role=normalized_role)
        return self._create_session(user)

    def login_user(self, *, email: str, password: str) -> AuthSession:
        try:
            user = self._store.authenticate(email=email, password=password)
        except (InvalidCredentialsError, ValueError) as exc:
            raise InvalidCredentialsError(str(exc)) from exc
        return self._create_session(user)

    def refresh_session(self, *, refresh_token: str) -> AuthSession:
        user = self.resolve_current_user(refresh_token=refresh_token, token_type="refresh")
        return self._create_session(user)

    def resolve_current_user(
        self,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_type: str = "access",
    ) -> StoredUser:
        token = access_token if token_type == "access" else refresh_token
        if token is None:
            raise InvalidTokenError("Token is required.")

        try:
            claims = decode_token(token, self.secret_key, expected_token_type=token_type)
        except ValueError as exc:
            raise InvalidTokenError(str(exc)) from exc

        user_id = str(claims.get("sub", "")).strip()
        if not user_id:
            raise InvalidTokenError("Token subject is missing.")

        user = self._store.get_by_id(user_id)
        if user is None:
            raise InvalidTokenError("Token references an unknown user.")
        return user

    def _create_session(self, user: StoredUser) -> AuthSession:
        access_expires_in_seconds = self._settings.access_token_minutes * 60
        refresh_expires_in_seconds = self._settings.refresh_token_days * 24 * 60 * 60

        access_token = encode_token(
            build_token_claims(
                subject=user.id,
                email=user.email,
                role=user.role,
                token_type="access",
                expires_in_seconds=access_expires_in_seconds,
            ),
            self.secret_key,
        )
        refresh_token = encode_token(
            build_token_claims(
                subject=user.id,
                email=user.email,
                role=user.role,
                token_type="refresh",
                expires_in_seconds=refresh_expires_in_seconds,
            ),
            self.secret_key,
        )

        return AuthSession(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in_seconds=access_expires_in_seconds,
            refresh_expires_in_seconds=refresh_expires_in_seconds,
        )
