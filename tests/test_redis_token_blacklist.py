from __future__ import annotations

import time
from pathlib import Path

from app.core.token_blacklist import RedisTokenBlacklist, TokenBlacklist, build_token_blacklist


class FakeRedisClient:
    def __init__(self) -> None:
        self._values: dict[str, float | None] = {}

    def ping(self) -> bool:
        return True

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._values[key] = time.time() + ex if ex is not None else None

    def exists(self, key: str) -> int:
        expiry = self._values.get(key)
        if expiry is None:
            return 1 if key in self._values else 0
        if expiry <= time.time():
            self._values.pop(key, None)
            return 0
        return 1

    def scan_iter(self, match: str | None = None):
        for key in list(self._values):
            expiry = self._values[key]
            if expiry is not None and expiry <= time.time():
                self._values.pop(key, None)
                continue
            if match is None:
                yield key
                continue
            if match.endswith("*"):
                if key.startswith(match[:-1]):
                    yield key
            elif key == match:
                yield key


def test_redis_token_blacklist_revokes_and_counts_entries() -> None:
    client = FakeRedisClient()
    blacklist = RedisTokenBlacklist(client=client, key_prefix="sakhi:blacklist")

    future_expiry = time.time() + 60
    blacklist.revoke("jti-123", future_expiry)

    assert blacklist.is_revoked("jti-123") is True
    assert blacklist.is_revoked("jti-xyz") is False
    assert blacklist.size == 1


def test_redis_token_blacklist_ignores_already_expired_tokens() -> None:
    client = FakeRedisClient()
    blacklist = RedisTokenBlacklist(client=client, key_prefix="sakhi:blacklist")

    blacklist.revoke("expired-jti", time.time() - 1)

    assert blacklist.is_revoked("expired-jti") is False
    assert blacklist.size == 0


def test_build_token_blacklist_returns_redis_backend_when_client_is_provided() -> None:
    client = FakeRedisClient()
    blacklist = build_token_blacklist(backend="redis", redis_client=client)

    assert isinstance(blacklist, RedisTokenBlacklist)
    blacklist.revoke("jti-abc", time.time() + 60)
    assert blacklist.is_revoked("jti-abc") is True


def test_build_token_blacklist_keeps_memory_backend_by_default() -> None:
    blacklist = build_token_blacklist()

    assert isinstance(blacklist, TokenBlacklist)

