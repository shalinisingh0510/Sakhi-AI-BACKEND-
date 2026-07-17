from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class RateLimiter:
    def __init__(self, requests_per_minute: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self.requests: defaultdict[str, list[datetime]] = defaultdict(list)

    def is_allowed(self, identifier: str) -> bool:
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] if req_time > minute_ago
        ]

        # Check if under limit
        if len(self.requests[identifier]) >= self.requests_per_minute:
            return False

        # Record this request
        self.requests[identifier].append(now)
        return True

    def get_remaining_requests(self, identifier: str) -> int:
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)

        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] if req_time > minute_ago
        ]

        return max(0, self.requests_per_minute - len(self.requests[identifier]))


# Global rate limiter instance
_rate_limiter = RateLimiter(requests_per_minute=60)
_rate_limiting_enabled = True


def configure_rate_limiter(requests_per_minute: int) -> None:
    """Configure the rate limiter with custom limits."""
    global _rate_limiter
    _rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)


def enable_rate_limiting(enabled: bool = True) -> None:
    """Enable or disable rate limiting globally."""
    global _rate_limiting_enabled
    _rate_limiting_enabled = enabled


def get_client_identifier(request: Request) -> str:
    """Get a unique identifier for the client (IP address or user ID)."""
    # Try to get user ID from token if available
    auth_header = request.headers.get("authorization", "")
    if auth_header and auth_header.startswith("Bearer "):
        # Use a hash of the token as identifier for authenticated users
        import hashlib
        token_hash = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
        return f"user:{token_hash}"
    
    # Fall back to IP address
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    return f"ip:{client_ip}"


async def rate_limit_middleware(request: Request, call_next: Callable) -> JSONResponse:
    """Rate limiting middleware to prevent API abuse."""
    # Skip rate limiting if disabled
    if not _rate_limiting_enabled:
        return await call_next(request)
    
    identifier = get_client_identifier(request)
    
    # Skip rate limiting for health endpoint
    if request.url.path == "/" or request.url.path == "/api/v1/health":
        return await call_next(request)
    
    if not _rate_limiter.is_allowed(identifier):
        remaining = _rate_limiter.get_remaining_requests(identifier)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "remaining_requests": remaining,
            },
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = _rate_limiter.get_remaining_requests(identifier)
    response.headers["X-RateLimit-Limit"] = str(_rate_limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return response


def add_security_headers(response: JSONResponse) -> JSONResponse:
    """Add security headers to the response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


async def security_headers_middleware(request: Request, call_next: Callable) -> JSONResponse:
    """Middleware to add security headers to all responses."""
    response = await call_next(request)
    return add_security_headers(response)


async def request_size_middleware(request: Request, call_next: Callable) -> JSONResponse:
    """Middleware to limit request size."""
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB
    
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size = int(content_length)
            if size > MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={"detail": f"Request body too large. Maximum size is {MAX_REQUEST_SIZE} bytes."},
                )
        except ValueError:
            pass
    
    return await call_next(request)
