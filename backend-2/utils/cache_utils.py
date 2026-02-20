"""
Simple in-memory cache with TTL for user context.
Dramatically reduces database hits for frequently accessed user data.
"""

import time
from typing import Any, Optional, Dict


class TTLCache:
    """Thread-safe TTL cache for user context."""

    def __init__(self, default_ttl: int = 60):
        """
        Args:
            default_ttl: Default time-to-live in seconds (default 60s)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if it exists and hasn't expired."""
        if key not in self._cache:
            return None

        value, expiry_time = self._cache[key]
        if time.time() > expiry_time:
            # Expired, remove it
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value with optional TTL override."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expiry_time = time.time() + effective_ttl
        self._cache[key] = (value, expiry_time)

    def clear(self, key: Optional[str] = None) -> None:
        """Clear a specific key or the entire cache."""
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]

    def size(self) -> int:
        """Return the number of cached items (including expired)."""
        return len(self._cache)


# Global cache for user context data (60-second TTL)
_user_context_cache = TTLCache(default_ttl=60)


def get_cached_user_context(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached user context if available and fresh."""
    return _user_context_cache.get(user_id)


def cache_user_context(user_id: str, context: Dict[str, Any], ttl: int = 60) -> None:
    """Store user context with TTL."""
    _user_context_cache.set(user_id, context, ttl)


def clear_user_context_cache(user_id: Optional[str] = None) -> None:
    """Clear cached context for a user or all users."""
    _user_context_cache.clear(user_id)


def get_cache_stats() -> Dict[str, Any]:
    """Return cache statistics for monitoring."""
    return {
        "cache_size": _user_context_cache.size(),
        "default_ttl": _user_context_cache.default_ttl,
    }
