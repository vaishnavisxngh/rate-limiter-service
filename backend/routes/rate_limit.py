"""
endpoints that are themselves rate-limited.

GET  /api/data          – demo endpoint using Token Bucket
GET  /api/data/sliding  – same demo using Sliding Window

Both endpoints:
  1. Extract the caller's IP address.
  2. Run the chosen algorithm.
  3. Track metrics.
  4. Return data (200) or a 429 with helpful headers.
"""

import time
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from redis_client import get_redis
from limiter import token_bucket_check, sliding_window_check, track_metrics

router = APIRouter(tags=["Rate Limited Endpoints"])

# Helper

def get_client_ip(request: Request) -> str:
    """
    Extract the real IP address from the request.
    Behind a reverse proxy the actual IP is in X-Forwarded-For.
    Fall back to the direct connection address.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can be a comma-separated list; take the first entry
        return forwarded_for.split(",")[0].strip()
    return request.client.host

# Token Bucket endpoint

@router.get("/api/data")
async def get_data_token_bucket(request: Request):
    """
    Rate-limited demo endpoint using the **Token Bucket** algorithm.

    Returns 200 with fake payload while the caller is within their limit.
    Returns 429 once the bucket is empty, with:
        X-RateLimit-Limit     – max tokens
        X-RateLimit-Remaining – tokens left (0 when blocked)
        Retry-After           – seconds until next allowed request
    """
    r = get_redis()
    ip = get_client_ip(request)

    result = token_bucket_check(r, ip)
    track_metrics(r, ip, result["allowed"])

    if result["allowed"]:
        return JSONResponse(
            status_code=200,
            content={
                "data": "Here is your requested data 🎉",
                "timestamp": time.time(),
                "algorithm": "token_bucket",
                "remaining_requests": result["remaining"],
            },
            headers={
                "X-RateLimit-Limit": str(result["limit"]),
                "X-RateLimit-Remaining": str(result["remaining"]),
            },
        )

    # Blocked
    raise HTTPException(
        status_code=429,
        detail={
            "error": "Too Many Requests",
            "message": f"Rate limit exceeded. Try again in {result.get('retry_after', 0)} seconds.",
            "retry_after": result.get("retry_after", 0),
        },
        headers={
            "X-RateLimit-Limit": str(result["limit"]),
            "X-RateLimit-Remaining": "0",
            "Retry-After": str(result.get("retry_after", 60)),
        },
    )

# Sliding Window endpoint

@router.get("/api/data/sliding")
async def get_data_sliding_window(request: Request):
    """
    Rate-limited demo endpoint using the **Sliding Window** algorithm.
    Identical contract to /api/data but uses a different algorithm under
    the hood so you can compare behaviour.
    """
    r = get_redis()
    ip = get_client_ip(request)

    result = sliding_window_check(r, ip)
    track_metrics(r, ip, result["allowed"])

    if result["allowed"]:
        return JSONResponse(
            status_code=200,
            content={
                "data": "Here is your requested data (sliding window) 🎉",
                "timestamp": time.time(),
                "algorithm": "sliding_window",
                "remaining_requests": result["remaining"],
            },
            headers={
                "X-RateLimit-Limit": str(result["limit"]),
                "X-RateLimit-Remaining": str(result["remaining"]),
            },
        )

    raise HTTPException(
        status_code=429,
        detail={
            "error": "Too Many Requests",
            "message": f"Rate limit exceeded. Try again in {result.get('retry_after', 0)} seconds.",
            "retry_after": result.get("retry_after", 0),
        },
        headers={
            "X-RateLimit-Limit": str(result["limit"]),
            "X-RateLimit-Remaining": "0",
            "Retry-After": str(result.get("retry_after", 60)),
        },
    )
