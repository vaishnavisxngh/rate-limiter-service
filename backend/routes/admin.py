"""
routes/admin.py
~~~~~~~~~~~~~~~
Admin-only endpoints for managing the rate limiter at runtime.

POST   /admin/reset/{identifier}  – reset one user's counters + bucket
DELETE /admin/reset-all           – wipe all rate-limit & metric keys
POST   /admin/config              – update algorithm parameters live
GET    /admin/config              – read current configuration
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from redis_client import get_redis

router = APIRouter(prefix="/admin", tags=["Admin"])

# Request / Response models

class ConfigUpdate(BaseModel):
    max_tokens: float = Field(default=10, gt=0, description="Max bucket capacity (token bucket)")
    refill_rate: float = Field(default=0.1, gt=0, description="Tokens added per second")
    max_requests: int = Field(default=10, gt=0, description="Max requests per window (sliding window)")
    window_seconds: int = Field(default=60, gt=0, description="Window size in seconds (sliding window)")

# Routes

@router.post("/reset/{identifier}")
async def reset_user(identifier: str):
    """
    Reset all Redis state for a single user identified by their IP address.

    Deletes:
      - token_bucket:<identifier>
      - sliding_window:<identifier>
      - metrics:user:<identifier>:total
      - metrics:user:<identifier>:blocked
    """
    r = get_redis()

    keys_to_delete = [
        f"token_bucket:{identifier}",
        f"sliding_window:{identifier}",
        f"metrics:user:{identifier}:total",
        f"metrics:user:{identifier}:blocked",
    ]

    deleted_count = r.delete(*keys_to_delete)

    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for identifier '{identifier}'. Nothing was deleted.",
        )

    return {
        "message": f"User '{identifier}' has been reset successfully.",
        "keys_deleted": deleted_count,
    }

@router.delete("/reset-all")
async def reset_all():
    """
    Delete ALL rate-limit and metrics keys from Redis.

    Uses SCAN + pattern matching instead of FLUSHDB so we only delete
    the keys that belong to this application (safe in shared Redis).
    """
    r = get_redis()

    patterns = [
        "token_bucket:*",
        "sliding_window:*",
        "metrics:*",
    ]

    total_deleted = 0
    for pattern in patterns:
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match=pattern, count=100)
            if keys:
                total_deleted += r.delete(*keys)
            if cursor == 0:
                break

    return {
        "message": "All rate-limit and metrics data has been cleared.",
        "keys_deleted": total_deleted,
    }


@router.post("/config")
async def update_config(config: ConfigUpdate):
    """
    Update algorithm parameters at runtime — no restart required.

    The values are stored in Redis so all instances pick them up
    immediately on the next request.
    """
    r = get_redis()

    r.set("config:max_tokens", config.max_tokens)
    r.set("config:refill_rate", config.refill_rate)
    r.set("config:max_requests", config.max_requests)
    r.set("config:window_seconds", config.window_seconds)

    return {
        "message": "Configuration updated successfully.",
        "config": config.model_dump(),
    }


@router.get("/config")
async def get_config():
    """
    Return the current configuration.
    Falls back to environment variables / hard-coded defaults if no
    config has been stored in Redis yet.
    """
    r = get_redis()

    return {
        "max_tokens": float(r.get("config:max_tokens") or os.getenv("RATE_LIMIT_REQUESTS", 10)),
        "refill_rate": float(r.get("config:refill_rate") or 0.1),
        "max_requests": int(float(r.get("config:max_requests") or os.getenv("RATE_LIMIT_REQUESTS", 10))),
        "window_seconds": int(float(r.get("config:window_seconds") or os.getenv("RATE_LIMIT_WINDOW", 60))),
    }
