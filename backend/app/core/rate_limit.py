"""
Minimal in-memory sliding-window rate limiter.

Good enough for a single backend process protecting login/forgot-password
from brute-forcing. If you ever run multiple backend instances behind a
load balancer, swap this for a Redis-backed limiter instead — an in-memory
dict won't be shared across processes.
"""

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()

    def _cleanup_unlocked(self, now: float) -> None:
        """Periodically prune stale keys to prevent memory leaks from millions of keys."""
        if now - self._last_cleanup < 60.0 and len(self._hits) < 1000:
            return
        self._last_cleanup = now
        stale_keys = [k for k, timestamps in self._hits.items() if not timestamps or now - timestamps[-1] >= self.window_seconds]
        for k in stale_keys:
            self._hits.pop(k, None)

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._cleanup_unlocked(now)
            recent = [t for t in self._hits[key] if now - t < self.window_seconds]
            if len(recent) >= self.max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts — please wait a few minutes and try again.",
                )
            recent.append(now)
            self._hits[key] = recent


# Per-account rate limiters (Key: "ip:email")
login_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=300)
forgot_password_limiter = InMemoryRateLimiter(max_attempts=3, window_seconds=600)
register_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=600)
reset_password_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=600)
resend_verification_limiter = InMemoryRateLimiter(max_attempts=4, window_seconds=600)

# IP-wide rate limiters (protects against credential stuffing, password spraying, and bot spam across multiple accounts)
login_ip_limiter = InMemoryRateLimiter(max_attempts=30, window_seconds=300)
register_ip_limiter = InMemoryRateLimiter(max_attempts=15, window_seconds=600)
forgot_password_ip_limiter = InMemoryRateLimiter(max_attempts=15, window_seconds=600)
resend_verification_ip_limiter = InMemoryRateLimiter(max_attempts=15, window_seconds=600)


def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP address, accounting for reverse proxies
    (Render, Cloudflare, AWS ALB) via the X-Forwarded-For header.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # The first IP in the comma-separated list is the original client IP
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_key(request: Request, identifier: str) -> str:
    client_ip = get_client_ip(request)
    return f"{client_ip}:{identifier.strip().lower()}"
