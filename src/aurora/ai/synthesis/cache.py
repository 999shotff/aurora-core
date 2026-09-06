"""Content-Hash Caching for synthesis results.

Cache deterministic synthesis inputs/results using content hash.
Incorporates question, evidence IDs, memory IDs, and configuration.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from aurora.ai.synthesis.schemas import SynthesisResult


class SynthesisCache:
    """Content-hash based cache for synthesis results."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._cache: dict[str, tuple[float, SynthesisResult]] = {}
        self._ttl = ttl_seconds

    def get(self, cache_key: str) -> SynthesisResult | None:
        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        ts, result = entry
        if time.monotonic() - ts > self._ttl:
            del self._cache[cache_key]
            return None
        return result

    def put(self, cache_key: str, result: SynthesisResult) -> None:
        self._cache[cache_key] = (time.monotonic(), result)
        if len(self._cache) > 128:
            self._evict_oldest()

    def invalidate(self, cache_key: str) -> None:
        self._cache.pop(cache_key, None)

    def clear(self) -> None:
        self._cache.clear()

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
        del self._cache[oldest_key]


def compute_cache_key(
    question: str,
    investigation_id: str | None,
    evidence_ids: list[str],
    memory_ids: list[str],
    domain: str,
) -> str:
    """Compute deterministic cache key from synthesis inputs."""
    payload = json.dumps({
        "q": question,
        "inv": investigation_id,
        "ev": sorted(evidence_ids),
        "mem": sorted(memory_ids),
        "dom": domain,
    }, sort_keys=True)
    h = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"synth-{h}"
