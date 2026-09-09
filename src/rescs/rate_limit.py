"""In-memory sliding-window rate limiter (single-instance).

Disabled by default (`RESCS_RATE_LIMIT_ENABLED=false`). When enabled,
buckets are keyed by API key + route class (general / writes / uploads).
Exceeded requests get 429 + Retry-After. Documented as single-instance;
multi-instance deployments need a shared backend (Redis) — external work.
"""

from __future__ import annotations

import time
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from rescs.config import Settings


def _bucket(path: str, method: str) -> str:
    if path.startswith("/api/v1/uploads") or (path.startswith("/api/v1/files") and method == "POST"):
        return "uploads"
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "writes"
    return "general"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self._settings = settings
        self._hits: dict[str, deque[float]] = {}

    async def dispatch(self, request: Request, call_next):
        settings = self._settings
        # Health/meta never limited; disabled flag skips everything (tests stay fast).
        if not settings.rate_limit_enabled or request.url.path.startswith("/health") or request.url.path == "/":
            return await call_next(request)
        bucket = _bucket(request.url.path, request.method)
        limits = {
            "general": settings.rate_limit_general_per_minute,
            "writes": settings.rate_limit_writes_per_minute,
            "uploads": settings.rate_limit_uploads_per_minute,
        }
        limit = limits[bucket]
        if not limit:
            return await call_next(request)
        key = f"{request.headers.get('X-API-Key', 'anon')}:{bucket}"
        now = time.monotonic()
        window = self._hits.setdefault(key, deque())
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= limit:
            retry = max(1, int(window[0] + 60 - now))
            # Best-effort audit of throttled requests is done by access logs; keep 429 stable.
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "rate limit exceeded", "details": {"bucket": bucket, "limit": limit}}},
                headers={"Retry-After": str(retry)},
            )
        window.append(now)
        response = await call_next(request)
        # Echo limit info for observability.
        response.headers.setdefault("X-RateLimit-Limit", str(limit))
        response.headers.setdefault("X-RateLimit-Remaining", str(max(0, limit - len(window))))
        return response
