"""Rate limit protection for provider requests.

Respects provider limits. Request throttling, exponential backoff,
maximum retry count. Never creates uncontrolled request loops.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Per-provider rate limiter with token bucket algorithm.

    Args:
        requests_per_minute: Maximum requests per minute.
        burst: Maximum burst size.
    """
    requests_per_minute: float = 60.0
    burst: float = 10.0
    _tokens: float = field(default=0.0, init=False)
    _last_refill: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        self._tokens = self.burst
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.burst,
            self._tokens + elapsed * (self.requests_per_minute / 60.0),
        )
        self._last_refill = now

    def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed."""
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def wait_time(self) -> float:
        """Seconds until next token available."""
        self._refill()
        if self._tokens >= 1.0:
            return 0.0
        return (1.0 - self._tokens) / (self.requests_per_minute / 60.0)


@dataclass
class RetryPolicy:
    """Exponential backoff retry policy."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    _attempt: int = field(default=0, init=False)

    def delay(self) -> float:
        """Calculate delay for current attempt."""
        d = min(self.base_delay * (2 ** self._attempt), self.max_delay)
        self._attempt += 1
        return d

    @property
    def should_retry(self) -> bool:
        return self._attempt < self.max_retries

    def reset(self) -> None:
        self._attempt = 0


class RequestThrottler:
    """Throttles requests across multiple providers.

    Tracks per-provider rate limiters.
    """

    def __init__(self) -> None:
        self._limiters: dict[str, RateLimiter] = {}
        self._retry_policies: dict[str, RetryPolicy] = {}

    def get_limiter(self, provider: str) -> RateLimiter:
        if provider not in self._limiters:
            self._limiters[provider] = RateLimiter()
        return self._limiters[provider]

    def get_retry_policy(self, provider: str) -> RetryPolicy:
        if provider not in self._retry_policies:
            self._retry_policies[provider] = RetryPolicy()
        return self._retry_policies[provider]

    def can_request(self, provider: str) -> bool:
        """Check if a request to the provider is allowed."""
        return self.get_limiter(provider).acquire()

    def reset_retry(self, provider: str) -> None:
        self.get_retry_policy(provider).reset()
