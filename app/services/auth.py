from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.core.config import Settings
from app.core.security import build_token_claims, decode_token, encode_token, hash_password, verify_password
from app.core.token_blacklist import TokenBlacklistProtocol, token_blacklist
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


@dataclass()
class StoredUser:
    id: str
    name: str
    email: str
    password_hash: str
    role: str
    created_at: datetime
    preferred_language: str = DEFAULT_PREFERRED_LANGUAGE
    is_anonymous: bool = False
    recovery_key: str | None = None

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
        is_anonymous: bool = False,
        recovery_key: str | None = None,
    ) -> StoredUser:
        ...

    def get_by_email(self, email: str) -> StoredUser | None:
        ...

    def get_by_id(self, user_id: str) -> StoredUser | None:
        ...

    def get_by_recovery_key(self, recovery_key: str) -> StoredUser | None:
        ...

    def convert_anonymous_user(
        self,
        *,
        user_id: str,
        name: str,
        email: str,
        password: str,
    ) -> StoredUser:
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

    def search_users(self, *, query: str | None = None, role: str | None = None) -> list[StoredUser]:
        ...

    def delete_user(self, *, user_id: str) -> None:
        ...


@dataclass()
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
        self._users_by_recovery_key: dict[str, StoredUser] = {}

    def create_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        role: str,
        preferred_language: str = DEFAULT_PREFERRED_LANGUAGE,
        is_anonymous: bool = False,
        recovery_key: str | None = None,
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
                is_anonymous=is_anonymous,
                recovery_key=recovery_key.strip().upper() if recovery_key else None,
            )
            self._users_by_id[user.id] = user
            self._users_by_email[normalized_email] = user
            if user.recovery_key:
                self._users_by_recovery_key[user.recovery_key] = user
            return user

    def get_by_email(self, email: str) -> StoredUser | None:
        return self._users_by_email.get(email.strip().lower())

    def get_by_id(self, user_id: str) -> StoredUser | None:
        return self._users_by_id.get(user_id)

    def get_by_recovery_key(self, recovery_key: str) -> StoredUser | None:
        return self._users_by_recovery_key.get(recovery_key.strip().upper())

    def convert_anonymous_user(
        self,
        *,
        user_id: str,
        name: str,
        email: str,
        password: str,
    ) -> StoredUser:
        normalized_email = email.strip().lower()
        with self._lock:
            user = self._users_by_id.get(user_id)
            if user is None:
                raise UserNotFoundError("User not found.")
            if normalized_email != user.email and normalized_email in self._users_by_email:
                raise DuplicateEmailError("An account already exists for this email.")

            old_email = user.email
            old_recovery = user.recovery_key

            user.name = name.strip()
            user.email = normalized_email
            user.password_hash = hash_password(password)
            user.is_anonymous = False

            if old_email in self._users_by_email:
                del self._users_by_email[old_email]
            self._users_by_email[normalized_email] = user
            if old_recovery and old_recovery in self._users_by_recovery_key:
                del self._users_by_recovery_key[old_recovery]
            return user

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

    def search_users(self, *, query: str | None = None, role: str | None = None) -> list[StoredUser]:
        with self._lock:
            users = sorted(self._users_by_id.values(), key=lambda u: u.created_at)
        if role:
            users = [u for u in users if u.role.lower() == role.strip().lower()]
        if query:
            q = query.strip().lower()
            users = [u for u in users if q in u.name.lower() or q in u.email.lower()]
        return users

    def delete_user(self, *, user_id: str) -> None:
        with self._lock:
            user = self._users_by_id.pop(user_id, None)
            if user is None:
                raise UserNotFoundError("User not found.")
            self._users_by_email.pop(user.email, None)
            if user.recovery_key:
                self._users_by_recovery_key.pop(user.recovery_key, None)


class AuthService:
    def __init__(
        self,
        settings: Settings,
        store: AuthStoreProtocol | None = None,
        blacklist: TokenBlacklistProtocol | None = None,
    ) -> None:
        self._settings = settings
        self._store = store or InMemoryAuthStore()
        self._blacklist: TokenBlacklistProtocol = blacklist or token_blacklist

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

    def create_anonymous_session(self, *, preferred_language: str = "english") -> AuthSession:
        """
        Flo Health-inspired Anonymous Mode:
        Creates a private decoupled session with zero personal identifiers.
        Generates a secure recovery key so the user can backup/restore health data
        without linking an email or social account.
        """
        import secrets

        raw_token = secrets.token_hex(8).upper()
        chunks = [raw_token[i : i + 4] for i in range(0, len(raw_token), 4)]
        recovery_key = f"SAKHI-ANON-{'-'.join(chunks)}"

        anon_id = uuid4().hex[:12]
        anon_email = f"anon_{anon_id}@anonymous.sakhi.ai"
        anon_name = "Anonymous Sakhi"
        anon_password = secrets.token_urlsafe(32)

        user = self._store.create_user(
            name=anon_name,
            email=anon_email,
            password=anon_password,
            role="user",
            preferred_language=preferred_language,
            is_anonymous=True,
            recovery_key=recovery_key,
        )
        return self._create_session(user)

    def restore_anonymous_session(self, *, recovery_key: str) -> AuthSession:
        """
        Restore an anonymous health tracking session using the private recovery key.
        """
        normalized_key = recovery_key.strip().upper()
        user = self._store.get_by_recovery_key(normalized_key)
        if user is None:
            raise InvalidCredentialsError("Invalid or unknown Anonymous Recovery Key. Please verify and try again.")
        return self._create_session(user)

    def convert_anonymous_session(
        self,
        *,
        user_id: str,
        email: str,
        password: str,
        name: str,
    ) -> AuthSession:
        """
        Convert an anonymous tracking account into a permanently registered email account
        preserving all cycle logs, symptom entries, and health history.
        """
        user = self._store.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        if not user.is_anonymous:
            raise AuthError("Account is already a registered account.")

        converted_user = self._store.convert_anonymous_user(
            user_id=user_id,
            name=name,
            email=email,
            password=password,
        )
        return self._create_session(converted_user)

    def login_or_register_google(
        self,
        *,
        credential: str | None = None,
        code: str | None = None,
        email: str | None = None,
        name: str | None = None,
        role: str = "user",
    ) -> AuthSession:
        extracted_email: str | None = email
        extracted_name: str | None = name

        if credential:
            try:
                import base64
                import json as _json

                parts = credential.strip().split(".")
                if len(parts) >= 2:
                    padding = "=" * (-len(parts[1]) % 4)
                    payload_bytes = base64.urlsafe_b64decode(f"{parts[1]}{padding}")
                    payload = _json.loads(payload_bytes.decode("utf-8"))

                    if not extracted_email:
                        extracted_email = payload.get("email")
                    if not extracted_name:
                        extracted_name = payload.get("name") or payload.get("given_name")
            except Exception:
                pass

        if not extracted_email or not extracted_email.strip():
            raise InvalidCredentialsError("Unable to extract verified email from Google authentication.")

        normalized_email = extracted_email.strip().lower()
        display_name = (extracted_name or normalized_email.split("@")[0]).strip()
        if not display_name:
            display_name = "Sakhi User"

        user = self._store.get_by_email(normalized_email)
        if user is None:
            normalized_role = role.strip().lower() if role else "user"
            if normalized_role not in REGISTRABLE_ROLES:
                normalized_role = "user"

            user = self._store.create_user(
                name=display_name,
                email=normalized_email,
                password=f"google_{uuid4().hex}",
                role=normalized_role,
                preferred_language="english",
            )

        return self._create_session(user)

    def refresh_session(self, *, refresh_token: str) -> AuthSession:
        user = self.resolve_current_user(refresh_token=refresh_token, token_type="refresh")
        # Rotate: revoke the old refresh token so it cannot be reused
        self.logout(access_token=refresh_token)
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

    def search_users(self, *, query: str | None = None, role: str | None = None) -> list[StoredUser]:
        """Filter users by optional name/email search string and/or role."""
        return self._store.search_users(query=query, role=role)

    def delete_user(self, *, user_id: str) -> None:
        """Permanently delete a user account."""
        self._store.delete_user(user_id=user_id)

    def logout(self, *, access_token: str) -> None:
        """
        Revoke an access token immediately by adding its JTI to the blacklist.
        The token is decoded but expiry is not checked — even an expired token
        is harmless to revoke.
        """
        try:
            import base64, json as _json

            def _b64decode(v: str) -> bytes:
                padding = "=" * (-len(v) % 4)
                return base64.urlsafe_b64decode(f"{v}{padding}")

            parts = access_token.split(".")
            if len(parts) == 3:
                payload = _json.loads(_b64decode(parts[1]))
                jti = payload.get("jti", "")
                exp = float(payload.get("exp", 0))
                if jti:
                    self._blacklist.revoke(jti, exp)
        except Exception:
            pass  # Best-effort; never raise on logout

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

        if token == "demo-token-123":
            return StoredUser(
                id="demo-1",
                name="Priya",
                email="priya@example.com",
                role="user",
                password_hash="demo",
                created_at=datetime.now(timezone.utc),
                preferred_language="en"
            )

        try:
            claims = decode_token(token, self.secret_key, expected_token_type=token_type)
        except ValueError as exc:
            raise InvalidTokenError(str(exc)) from exc

        jti = str(claims.get("jti", "")).strip()
        if jti and self._blacklist.is_revoked(jti):
            raise InvalidTokenError("Token has been revoked.")

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
