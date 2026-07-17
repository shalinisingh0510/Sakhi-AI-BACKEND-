"""
In-process token blacklist for immediate session revocation (logout).

Stores revoked JTI (JWT ID) values with their expiry time.
Expired entries are cleaned up automatically on each check so memory
stays bounded without a background thread.

For multi-process / multi-node deployments this should be replaced with
a Redis SET with TTL per entry.  The interface is the same — just swap
the implementation of `TokenBlacklist`.
"""
from __future__ import annotations

import time
from threading import RLock


class TokenBlacklist:
    def __init__(self) -> None:
        self._lock = RLock()
        # Maps jti -> expiry_unix_timestamp
        self._revoked: dict[str, float] = {}

    def revoke(self, jti: str, expires_at: float) -> None:
        """Mark a token JTI as revoked until its natural expiry time."""
        with self._lock:
            self._revoked[jti] = expires_at
            self._purge_expired()

    def is_revoked(self, jti: str) -> bool:
        """Return True if the JTI is on the blacklist and has not yet expired."""
        with self._lock:
            expiry = self._revoked.get(jti)
            if expiry is None:
                return False
            if expiry <= time.time():
                del self._revoked[jti]
                return False
            return True

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [jti for jti, exp in self._revoked.items() if exp <= now]
        for jti in expired:
            del self._revoked[jti]

    @property
    def size(self) -> int:
        """Number of currently active revoked tokens (for monitoring)."""
        with self._lock:
            self._purge_expired()
            return len(self._revoked)


# Singleton shared across the whole process
token_blacklist = TokenBlacklist()
