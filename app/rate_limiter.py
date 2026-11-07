import time
from fastapi import Request, HTTPException, status
import redis.asyncio as redis
from .config import settings
from .logging_config import logger

async def rate_limiter(request: Request):
    """
    FastAPI dependency to enforce Redis-backed rate limits per client IP.
    """
    # Exclude docs, openapi, and root endpoints from rate limiting if desired
    if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
        return

    # Extract client IP
    client_ip = request.client.host
    redis_client = redis.from_url(settings.REDIS_URL)
    
    # Standard sliding window or simple time-window
    current_time = int(time.time())
    window = current_time // 60
    redis_key = f"rate_limit:{client_ip}:{window}"
    
    try:
        # Atomic increment
        requests_count = await redis_client.incr(redis_key)
        if requests_count == 1:
            # Set TTL for the window
            await redis_client.expire(redis_key, 60)
            
        if requests_count > settings.RATE_LIMIT_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {requests_count} requests")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Rate limit exceeded."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiter Redis execution error: {str(e)}")
        # Fail open in case Redis goes down, or handle securely depending on policy
    finally:
        await redis_client.close()
