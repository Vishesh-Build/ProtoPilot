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


# 5 attempts per 5 minutes, keyed by "endpoint:client_ip:email"
login_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=300)
forgot_password_limiter = InMemoryRateLimiter(max_attempts=3, window_seconds=600)


def rate_limit_key(request: Request, identifier: str) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{client_ip}:{identifier.lower()}"
