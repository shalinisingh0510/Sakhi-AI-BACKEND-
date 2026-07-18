from __future__ import annotations

import time

from app.core.cache import InMemoryCacheBackend, RedisCacheBackend, build_cache_backend


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def get(self, key: str):
        return self.values.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)

    def incr(self, key: str) -> int:
        current = int(self.values.get(key, "0")) + 1
        self.values[key] = str(current)
        return current


def test_in_memory_cache_backend_tracks_values_and_versions() -> None:
    cache = InMemoryCacheBackend()

    assert cache.get_version("lessons") == 0
    cache.set("alpha", "bravo", ttl_seconds=60)
    assert cache.get("alpha") == "bravo"
    assert cache.bump_version("lessons") == 1
    assert cache.get_version("lessons") == 1
    cache.delete("alpha")
    assert cache.get("alpha") is None


def test_redis_cache_backend_and_factory_use_same_key_space() -> None:
    client = FakeRedisClient()
    backend = build_cache_backend(backend="redis", redis_client=client, redis_key_prefix="sakhi:test")

    assert isinstance(backend, RedisCacheBackend)
    backend.set("alpha", "bravo")
    assert backend.get("alpha") == "bravo"
    assert backend.get_version("lessons") == 0
    assert backend.bump_version("lessons") == 1
    assert backend.get_version("lessons") == 1
    backend.delete("alpha")
    assert backend.get("alpha") is None


def test_build_cache_backend_falls_back_to_memory_on_unknown_backend() -> None:
    backend = build_cache_backend(backend="unknown-backend")

    assert isinstance(backend, InMemoryCacheBackend)

