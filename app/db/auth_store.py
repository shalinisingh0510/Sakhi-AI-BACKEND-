from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.core.security import hash_password, verify_password
from app.services.auth import DuplicateEmailError, InvalidCredentialsError, StoredUser


class SQLiteAuthStore:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        self._lock = RLock()
        self._connection = sqlite3.connect(self._database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    def _row_to_user(self, row: sqlite3.Row) -> StoredUser:
        created_at = datetime.fromisoformat(row["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return StoredUser(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=row["role"],
            created_at=created_at,
        )

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
        user_id = uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        password_hash = hash_password(password)

        try:
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    INSERT INTO users (id, name, email, password_hash, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, name.strip(), normalized_email, password_hash, normalized_role, created_at),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateEmailError("An account already exists for this email.") from exc

        user = self.get_by_id(user_id)
        if user is None:
            raise RuntimeError("Stored user could not be loaded after insertion.")
        return user

    def get_by_email(self, email: str) -> StoredUser | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT id, name, email, password_hash, role, created_at FROM users WHERE email = ?",
                (email.strip().lower(),),
            ).fetchone()
        return None if row is None else self._row_to_user(row)

    def get_by_id(self, user_id: str) -> StoredUser | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT id, name, email, password_hash, role, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return None if row is None else self._row_to_user(row)

    def authenticate(self, *, email: str, password: str) -> StoredUser:
        user = self.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        return user
