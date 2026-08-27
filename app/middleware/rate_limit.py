import time
from fastapi import Request, HTTPException, status
from typing import Dict, Tuple

# Basic in-memory rate limiting. In production, use Redis!
_rate_limits: Dict[str, Tuple[int, float]] = {}

def check_rate_limit(request: Request, limit: int = 100, window: int = 60):
    """
    Very basic sliding window rate limiter per IP/User.
    Production would use Redis to avoid memory leaks and scale horizontally.
    """
    # For Phase 16 demonstration, we use client host or user id if available
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Try to extract user ID from state if available
    identifier = getattr(request.state, "user_id", client_ip)
    
    if identifier in _rate_limits:
        count, start_time = _rate_limits[identifier]
        if now - start_time > window:
            _rate_limits[identifier] = (1, now)
        elif count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        else:
            _rate_limits[identifier] = (count + 1, start_time)
    else:
        _rate_limits[identifier] = (1, now)

async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware to globally enforce rate limits.
    """
    # Apply global 200 requests / minute limit per IP
    check_rate_limit(request, limit=200, window=60)
    response = await call_next(request)
    return response
