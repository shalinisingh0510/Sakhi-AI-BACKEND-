from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import psycopg

from app.core.security import hash_password, verify_password
from app.services.auth import DuplicateEmailError, InvalidCredentialsError, StoredUser, UserNotFoundError


class PostgresAuthStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    preferred_language TEXT NOT NULL DEFAULT 'english',
                    created_at TEXT NOT NULL,
                    is_deleted INT NOT NULL DEFAULT 0,
                    deleted_at TEXT,
                    deleted_email TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    def _row_to_user(self, row: dict) -> StoredUser:
        created_at = datetime.fromisoformat(row["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        preferred_language = row["preferred_language"] if "preferred_language" in row.keys() else "english"
        return StoredUser(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=row["role"],
            preferred_language=preferred_language,
            created_at=created_at,
        )

    def create_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        role: str,
        preferred_language: str = "english",
    ) -> StoredUser:
        normalized_email = email.strip().lower()
        normalized_role = role.strip().lower()
        normalized_language = preferred_language.strip().lower()
        user_id = uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        password_hash = hash_password(password)

        try:
            with self._pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO users (id, name, email, password_hash, role, preferred_language, created_at, deleted_email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        name.strip(),
                        normalized_email,
                        password_hash,
                        normalized_role,
                        normalized_language,
                        created_at,
                        None,
                    ),
                )
        except psycopg.IntegrityError as exc:
            raise DuplicateEmailError("An account already exists for this email.") from exc

        user = self.get_by_id(user_id)
        if user is None:
            raise RuntimeError("Stored user could not be loaded after insertion.")
        return user

    def get_by_email(self, email: str) -> StoredUser | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(
                    "SELECT id, name, email, password_hash, role, preferred_language, created_at FROM users WHERE email = %s AND is_deleted = 0",
                    (email.strip().lower(),),
                ).fetchone()
        return None if row is None else self._row_to_user(row)

    def get_by_id(self, user_id: str) -> StoredUser | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(
                    "SELECT id, name, email, password_hash, role, preferred_language, created_at FROM users WHERE id = %s AND is_deleted = 0",
                    (user_id,),
                ).fetchone()
        return None if row is None else self._row_to_user(row)

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
        updates: list[str] = []
        params: list[str] = []

        if name is not None:
            normalized_name = name.strip()
            if not normalized_name:
                raise ValueError("Name cannot be empty.")
            updates.append("name = %s")
            params.append(normalized_name)

        if preferred_language is not None:
            normalized_language = preferred_language.strip().lower()
            if not normalized_language:
                raise ValueError("Preferred language cannot be empty.")
            updates.append("preferred_language = %s")
            params.append(normalized_language)

        if not updates:
            user = self.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError("User not found.")
            return user

        params.append(user_id)
        with self._pool.connection() as conn:
            cursor = conn.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
                params,
            )
        if cursor.rowcount == 0:
            raise UserNotFoundError("User not found.")

        user = self.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        return user

    def update_user_role(self, *, user_id: str, role: str) -> StoredUser:
        normalized_role = role.strip().lower()
        with self._pool.connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET role = %s WHERE id = %s",
                (normalized_role, user_id),
            )
        if cursor.rowcount == 0:
            raise UserNotFoundError("User not found.")

        user = self.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        return user

    def change_password(self, *, user_id: str, current_password: str, new_password: str) -> None:
        user = self.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect.")
        new_hash = hash_password(new_password)
        with self._pool.connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
            )
        if cursor.rowcount == 0:
            raise UserNotFoundError("User not found.")

    def list_users(self) -> list[StoredUser]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    "SELECT id, name, email, password_hash, role, preferred_language, created_at FROM users WHERE is_deleted = 0 ORDER BY created_at ASC"
                ).fetchall()
        return [self._row_to_user(row) for row in rows]

    def search_users(self, *, query: str | None = None, role: str | None = None) -> list[StoredUser]:
        conditions: list[str] = ["is_deleted = 0"]
        params: list[object] = []
        if role:
            conditions.append("LOWER(role) = %s")
            params.append(role.strip().lower())
        if query:
            q = f"%{query.strip().lower()}%"
            conditions.append("(LOWER(name) LIKE %s OR LOWER(email) LIKE %s)")
            params.extend([q, q])
        sql = "SELECT id, name, email, password_hash, role, preferred_language, created_at FROM users"
        sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY created_at ASC"
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(sql, params).fetchall()
        return [self._row_to_user(row) for row in rows]

    def delete_user(self, *, user_id: str) -> None:
        """Soft-delete: mark the user as deleted rather than removing the row."""
        deleted_at = datetime.now(timezone.utc).isoformat()
        tombstone_email = f"deleted-{user_id}@deleted.local"
        with self._pool.connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET is_deleted = 1, deleted_at = %s, deleted_email = email, email = %s WHERE id = %s AND is_deleted = 0",
                (deleted_at, tombstone_email, user_id),
            )
        if cursor.rowcount == 0:
            raise UserNotFoundError("User not found.")
