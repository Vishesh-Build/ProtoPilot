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

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._hits[key] if now - t < self.window_seconds]
            if len(recent) >= self.max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts — please wait a few minutes and try again.",
                )
            recent.append(now)
            self._hits[key] = recent


# Rate limiters for authentication endpoints:
login_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=300)
forgot_password_limiter = InMemoryRateLimiter(max_attempts=3, window_seconds=600)
register_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=600)
reset_password_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=600)


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
