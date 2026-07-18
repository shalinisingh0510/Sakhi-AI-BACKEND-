from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class CacheBackendProtocol(Protocol):
    def get(self, key: str) -> str | None:
        ...

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        ...

    def delete(self, key: str) -> None:
        ...

    def get_version(self, namespace: str) -> int:
        ...

    def bump_version(self, namespace: str) -> int:
        ...


@dataclass(slots=True)
class _CacheEntry:
    value: str
    expires_at: float | None = None


class InMemoryCacheBackend:
    def __init__(self) -> None:
        self._lock = RLock()
        self._values: dict[str, _CacheEntry] = {}
        self._versions: dict[str, int] = {}

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [key for key, entry in self._values.items() if entry.expires_at is not None and entry.expires_at <= now]
        for key in expired:
            self._values.pop(key, None)

    def get(self, key: str) -> str | None:
        with self._lock:
            self._purge_expired()
            entry = self._values.get(key)
            return None if entry is None else entry.value

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        expires_at = None if ttl_seconds is None else time.time() + ttl_seconds
        with self._lock:
            self._values[key] = _CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)

    def get_version(self, namespace: str) -> int:
        with self._lock:
            self._purge_expired()
            return self._versions.get(namespace, 0)

    def bump_version(self, namespace: str) -> int:
        with self._lock:
            current = self._versions.get(namespace, 0) + 1
            self._versions[namespace] = current
            return current


class RedisCacheBackend:
    def __init__(self, *, client: Any, key_prefix: str = "sakhi:cache") -> None:
        self._client = client
        self._key_prefix = key_prefix.strip().strip(":") or "sakhi:cache"

    def _data_key(self, key: str) -> str:
        return f"{self._key_prefix}:data:{key}"

    def _version_key(self, namespace: str) -> str:
        return f"{self._key_prefix}:version:{namespace}"

    def get(self, key: str) -> str | None:
        return self._client.get(self._data_key(key))

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds is None:
            self._client.set(self._data_key(key), value)
        else:
            self._client.set(self._data_key(key), value, ex=ttl_seconds)

    def delete(self, key: str) -> None:
        self._client.delete(self._data_key(key))

    def get_version(self, namespace: str) -> int:
        raw = self._client.get(self._version_key(namespace))
        return int(raw) if raw is not None else 0

    def bump_version(self, namespace: str) -> int:
        return int(self._client.incr(self._version_key(namespace)))


def build_cache_backend(
    *,
    backend: str = "memory",
    redis_url: str = "redis://localhost:6379/0",
    redis_key_prefix: str = "sakhi:cache",
    redis_client: Any | None = None,
) -> CacheBackendProtocol:
    normalized_backend = backend.strip().lower()
    if normalized_backend == "redis":
        try:
            client = redis_client
            if client is None:
                import redis as redis_module  # type: ignore

                client = redis_module.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return RedisCacheBackend(client=client, key_prefix=redis_key_prefix)
        except Exception as exc:
            logger.warning("Redis cache backend unavailable (%s). Falling back to in-memory cache.", exc)
    return InMemoryCacheBackend()


def build_cache_key(namespace: str, version: int, *parts: Any) -> str:
    raw = json.dumps(parts, separators=(",", ":"), ensure_ascii=False, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{namespace}:{version}:{digest}"
