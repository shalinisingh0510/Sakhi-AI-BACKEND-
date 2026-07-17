from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.core.config import Settings
from app.core.security import build_token_claims, decode_token, encode_token, hash_password, verify_password
from app.schemas.auth import PublicUser, SUPPORTED_LANGUAGES

DEFAULT_PREFERRED_LANGUAGE = "english"
REGISTRABLE_ROLES = {"user", "admin"}
SUPPORTED_ROLES = {"user", "admin", "moderator"}
SUPPORTED_LANGUAGE_SET = {language.lower() for language in SUPPORTED_LANGUAGES}


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


class InvalidProfileUpdateError(AuthError):
    pass


class UserNotFoundError(AuthError):
    pass


@dataclass(slots=True)
class StoredUser:
    id: str
    name: str
    email: str
    password_hash: str
    role: str
    created_at: datetime
    preferred_language: str = DEFAULT_PREFERRED_LANGUAGE

    def to_public_user(self) -> PublicUser:
        return PublicUser.model_validate(self)


class AuthStoreProtocol(Protocol):
    def create_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        role: str,
        preferred_language: str = DEFAULT_PREFERRED_LANGUAGE,
    ) -> StoredUser:
        ...

    def get_by_email(self, email: str) -> StoredUser | None:
        ...

    def get_by_id(self, user_id: str) -> StoredUser | None:
        ...

    def authenticate(self, *, email: str, password: str) -> StoredUser:
        ...

    def update_user_profile(
        self,
        *,
        user_id: str,
        name: str | None = None,
        preferred_language: str | None = None,
    ) -> StoredUser:
        ...

    def update_user_role(self, *, user_id: str, role: str) -> StoredUser:
        ...

    def change_password(self, *, user_id: str, current_password: str, new_password: str) -> None:
        ...

    def list_users(self) -> list[StoredUser]:
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
        preferred_language: str = DEFAULT_PREFERRED_LANGUAGE,
    ) -> StoredUser:
        normalized_email = email.strip().lower()
        normalized_role = role.strip().lower()
        normalized_language = preferred_language.strip().lower()

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
                preferred_language=normalized_language,
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

    def update_user_profile(
        self,
        *,
        user_id: str,
        name: str | None = None,
        preferred_language: str | None = None,
    ) -> StoredUser:
        with self._lock:
            user = self._users_by_id.get(user_id)
            if user is None:
                raise UserNotFoundError("User not found.")

            if name is not None:
                normalized_name = name.strip()
                if not normalized_name:
                    raise InvalidProfileUpdateError("Name cannot be empty.")
                user.name = normalized_name

            if preferred_language is not None:
                normalized_language = preferred_language.strip().lower()
                if normalized_language not in SUPPORTED_LANGUAGE_SET:
                    raise InvalidProfileUpdateError("Unsupported preferred language.")
                user.preferred_language = normalized_language

            self._users_by_email[user.email] = user
            return user

    def update_user_role(self, *, user_id: str, role: str) -> StoredUser:
        normalized_role = role.strip().lower()
        with self._lock:
            user = self._users_by_id.get(user_id)
            if user is None:
                raise UserNotFoundError("User not found.")
            user.role = normalized_role
            return user

    def change_password(self, *, user_id: str, current_password: str, new_password: str) -> None:
        with self._lock:
            user = self._users_by_id.get(user_id)
            if user is None:
                raise UserNotFoundError("User not found.")
            if not verify_password(current_password, user.password_hash):
                raise InvalidCredentialsError("Current password is incorrect.")
            user.password_hash = hash_password(new_password)

    def list_users(self) -> list[StoredUser]:
        with self._lock:
            return sorted(self._users_by_id.values(), key=lambda user: user.created_at)


class AuthService:
    def __init__(self, settings: Settings, store: AuthStoreProtocol | None = None) -> None:
        self._settings = settings
        self._store = store or InMemoryAuthStore()

    @property
    def secret_key(self) -> str:
        return self._settings.secret_key.get_secret_value()

    def register_user(self, *, name: str, email: str, password: str, role: str = "user") -> AuthSession:
        normalized_role = role.strip().lower()
        if normalized_role not in REGISTRABLE_ROLES:
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

    def update_profile(
        self,
        *,
        user_id: str,
        name: str | None = None,
        preferred_language: str | None = None,
    ) -> StoredUser:
        if name is None and preferred_language is None:
            raise InvalidProfileUpdateError("At least one profile field must be provided.")

        normalized_name = None if name is None else name.strip()
        if name is not None and not normalized_name:
            raise InvalidProfileUpdateError("Name cannot be empty.")

        normalized_language = None if preferred_language is None else preferred_language.strip().lower()
        if normalized_language is not None and normalized_language not in SUPPORTED_LANGUAGE_SET:
            raise InvalidProfileUpdateError("Unsupported preferred language.")

        return self._store.update_user_profile(
            user_id=user_id,
            name=normalized_name,
            preferred_language=normalized_language,
        )

    def update_user_role(self, *, user_id: str, role: str) -> StoredUser:
        normalized_role = role.strip().lower()
        if normalized_role not in SUPPORTED_ROLES:
            raise InvalidRoleError("Unsupported user role.")
        return self._store.update_user_role(user_id=user_id, role=normalized_role)

    def change_password(self, *, user_id: str, current_password: str, new_password: str) -> None:
        """Verify the current password then replace it with the new one."""
        if current_password == new_password:
            raise InvalidProfileUpdateError("New password must be different from the current password.")
        self._store.change_password(
            user_id=user_id,
            current_password=current_password,
            new_password=new_password,
        )

    def list_users(self) -> list[StoredUser]:
        return self._store.list_users()

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

        token_role = str(claims.get("role", "")).strip().lower()
        if token_role and token_role != user.role.strip().lower():
            raise InvalidTokenError("Token role no longer matches the current user record.")
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
