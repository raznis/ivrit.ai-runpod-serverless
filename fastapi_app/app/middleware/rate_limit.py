"""
Rate limiting middleware
"""
from fastapi import Request, HTTPException
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict
from typing import Dict, Tuple

from ..config import settings

# In-memory rate limit storage (use Redis in production)
rate_limit_storage: Dict[str, Tuple[int, datetime]] = defaultdict(lambda: (0, datetime.utcnow()))
rate_limit_lock = asyncio.Lock()


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware
    
    Tracks requests per API key and enforces rate limits
    """
    # Skip rate limiting for health and metrics endpoints
    if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Get API key from header
    api_key = request.headers.get(settings.API_KEY_HEADER)
    
    if api_key:
        async with rate_limit_lock:
            # Get current count and timestamp
            count, timestamp = rate_limit_storage[api_key]
            
            # Reset if period has elapsed
            if datetime.utcnow() - timestamp > timedelta(seconds=settings.RATE_LIMIT_PERIOD):
                count = 0
                timestamp = datetime.utcnow()
            
            # Check rate limit
            if count >= settings.RATE_LIMIT_REQUESTS:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_REQUESTS} requests per {settings.RATE_LIMIT_PERIOD} seconds."
                )
            
            # Increment count
            rate_limit_storage[api_key] = (count + 1, timestamp)
    
    response = await call_next(request)
    return response
