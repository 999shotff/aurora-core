"""Bounded in-memory cache for market data.

Prevents duplicate requests, bounded memory, clear invalidation rules.
No stale-data masquerading as live data.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Single cache entry with TTL."""
    key: str
    data: object
    created_at: float
    ttl_seconds: float

    @property
    def is_expired(self) -> bool:
        return time.monotonic() - self.created_at > self.ttl_seconds


class BoundedCache:
    """Fixed-size LRU cache with TTL expiration.

    Args:
        max_size: Maximum number of entries.
        default_ttl: Default TTL in seconds for cache entries.
    """

    def __init__(self, max_size: int = 256, default_ttl: float = 60.0) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> object | None:
        """Get value if exists and not expired."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.is_expired:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return entry.data

    def put(self, key: str, data: object, ttl: float | None = None) -> None:
        """Store value with optional TTL override."""
        if key in self._entries:
            del self._entries[key]
        elif len(self._entries) >= self._max_size:
            self._entries.popitem(last=False)
        self._entries[key] = CacheEntry(
            key=key,
            data=data,
            created_at=time.monotonic(),
            ttl_seconds=ttl if ttl is not None else self._default_ttl,
        )

    def invalidate(self, key: str) -> bool:
        """Remove a specific key. Returns True if key existed."""
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys starting with prefix. Returns count removed."""
        keys = [k for k in self._entries if k.startswith(prefix)]
        for k in keys:
            del self._entries[k]
        return len(keys)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def capacity(self) -> int:
        return self._max_size
