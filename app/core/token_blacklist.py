from __future__ import annotations

import logging
import math
import time
from threading import RLock
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class TokenBlacklistProtocol(Protocol):
    def revoke(self, jti: str, expires_at: float) -> None:
        ...

    def is_revoked(self, jti: str) -> bool:
        ...

    @property
    def size(self) -> int:
        ...


class TokenBlacklist:
    """In-process token blacklist for immediate session revocation."""

    def __init__(self) -> None:
        self._lock = RLock()
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


class RedisTokenBlacklist:
    """Redis-backed blacklist using per-token TTL for multi-node deployments."""

    def __init__(self, *, client: Any, key_prefix: str = "sakhi:token-blacklist") -> None:
        self._client = client
        self._key_prefix = key_prefix.strip().strip(":") or "sakhi:token-blacklist"

    def _key(self, jti: str) -> str:
        return f"{self._key_prefix}:{jti.strip()}"

    def revoke(self, jti: str, expires_at: float) -> None:
        ttl_seconds = int(math.ceil(expires_at - time.time()))
        if ttl_seconds <= 0:
            return
        self._client.set(self._key(jti), "1", ex=ttl_seconds)

    def is_revoked(self, jti: str) -> bool:
        return bool(self._client.exists(self._key(jti)))

    @property
    def size(self) -> int:
        pattern = f"{self._key_prefix}:*"
        return sum(1 for _ in self._client.scan_iter(match=pattern))


def build_token_blacklist(
    *,
    backend: str = "memory",
    redis_url: str = "redis://localhost:6379/0",
    redis_key_prefix: str = "sakhi:token-blacklist",
    redis_client: Any | None = None,
) -> TokenBlacklistProtocol:
    """Build the configured token blacklist backend.

    Falls back to the in-process implementation if Redis is unavailable.
    """
    normalized_backend = backend.strip().lower()
    if normalized_backend == "redis":
        try:
            client = redis_client
            if client is None:
                import redis as redis_module  # type: ignore

                client = redis_module.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return RedisTokenBlacklist(client=client, key_prefix=redis_key_prefix)
        except Exception as exc:
            logger.warning("Redis token blacklist unavailable (%s). Falling back to in-memory blacklist.", exc)
    return TokenBlacklist()


# Backwards-compatible singleton for callers that still import the module-level instance.
token_blacklist = TokenBlacklist()
