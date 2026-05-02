"""
data/cache.py — Simple in-memory TTL cache to avoid redundant API calls
"""
from __future__ import annotations

import time
from typing import Any, Optional


class TTLCache:
    """Thread-safe TTL dict cache."""

    def __init__(self, ttl_seconds: int = 300):
        self._store: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            value, ts = self._store[key]
            if time.monotonic() - ts < self._ttl:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.monotonic())

    def clear(self) -> None:
        self._store.clear()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


# Global session cache instance
_cache = TTLCache(ttl_seconds=300)


def cache_key(*parts) -> str:
    return "|".join(str(p) for p in parts)


def get_cached(key: str) -> Optional[Any]:
    return _cache.get(key)


def set_cached(key: str, value: Any) -> None:
    _cache.set(key, value)


def clear_cache() -> None:
    _cache.clear()
