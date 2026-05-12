"""
limiter.py
Core rate-limiting algorithms + metrics tracking.

Two algorithms are implemented:
  1. Token Bucket  – allows short bursts, refills tokens over time.
  2. Sliding Window – counts requests in a rolling time window.

Both store their state in Redis so every FastAPI instance shares the
same counters → that's what makes the service *distributed*.
"""

import time
import json
import os
from redis import Redis

# Helpers

def _get_config(r: Redis, key: str, default: float) -> float:
    """Read a config value from Redis, fall back to the given default."""
    val = r.get(f"config:{key}")
    return float(val) if val is not None else default

# Algorithm 1 — Token Bucket

def token_bucket_check(
    r: Redis,
    identifier: str,
    max_tokens: float | None = None,
    refill_rate: float | None = None,
) -> dict:
    """
    Check whether *identifier* (usually an IP address) is allowed to make
    a request under the Token Bucket algorithm.

    Redis keys used
    ---------------
    token_bucket:<identifier>  →  Hash with fields:
        tokens       – current token count (float stored as string)
        last_refill  – Unix timestamp of the last refill (float)

    Parameters
    ----------
    r            Redis client
    identifier   Unique key for the caller (IP, API key, …)
    max_tokens   Maximum bucket capacity.  Falls back to Redis config,
                 then to the RATE_LIMIT_REQUESTS env-var (default 10).
    refill_rate  Tokens added per second.  Falls back to Redis config,
                 then to 0.1 (= 1 token every 10 seconds).

    Returns
    -------
    dict with keys:
        allowed      bool
        remaining    int   – tokens left after this request
        limit        int   – max_tokens in use
        retry_after  float – seconds to wait (only when allowed=False)
        algorithm    str   – "token_bucket"
    """
    if max_tokens is None:
        max_tokens = _get_config(r, "max_tokens", float(os.getenv("RATE_LIMIT_REQUESTS", 10)))
    if refill_rate is None:
        refill_rate = _get_config(r, "refill_rate", 0.1)

    redis_key = f"token_bucket:{identifier}"
    now = time.time()

    # --- Fetch existing bucket data from Redis ---
    data = r.hgetall(redis_key)

    if not data:
        # First request from this identifier → full bucket
        tokens = max_tokens - 1          # consume 1 immediately
        last_refill = now
    else:
        tokens = float(data["tokens"])
        last_refill = float(data["last_refill"])

        # Refill based on elapsed time
        elapsed = now - last_refill
        tokens_to_add = elapsed * refill_rate
        tokens = min(max_tokens, tokens + tokens_to_add)
        last_refill = now

    # --- Decision ---
    if tokens >= 1:
        tokens -= 1
        allowed = True
        retry_after = 0.0
    else:
        allowed = False
        # How long until the bucket has 1 full token?
        retry_after = round((1 - tokens) / refill_rate, 2)

    # --- Persist updated bucket (expire after 1 hour of inactivity) ---
    r.hset(redis_key, mapping={"tokens": tokens, "last_refill": last_refill})
    r.expire(redis_key, 3600)

    result = {
        "allowed": allowed,
        "remaining": max(0, int(tokens)),
        "limit": int(max_tokens),
        "algorithm": "token_bucket",
    }
    if not allowed:
        result["retry_after"] = retry_after

    return result


# ---------------------------------------------------------------------------
# Algorithm 2 — Sliding Window (using Redis Sorted Sets)
# ---------------------------------------------------------------------------

def sliding_window_check(
    r: Redis,
    identifier: str,
    max_requests: int | None = None,
    window_seconds: int | None = None,
) -> dict:
    """
    Check whether *identifier* is allowed under the Sliding Window algorithm.

    Redis keys used
    sliding_window:<identifier>  →  Sorted Set where
        member = "<timestamp_ms>-<random_suffix>"
        score  = timestamp in milliseconds

    Old entries (outside the window) are pruned on every request so the
    set never grows unbounded.

    Returns
    dict with keys:
        allowed      bool
        remaining    int
        limit        int
        retry_after  float  (only when allowed=False)
        algorithm    str    – "sliding_window"
    """
    if max_requests is None:
        max_requests = int(_get_config(r, "max_requests", float(os.getenv("RATE_LIMIT_REQUESTS", 10))))
    if window_seconds is None:
        window_seconds = int(_get_config(r, "window_seconds", float(os.getenv("RATE_LIMIT_WINDOW", 60))))

    redis_key = f"sliding_window:{identifier}"
    now_ms = int(time.time() * 1000)          # milliseconds
    window_start_ms = now_ms - (window_seconds * 1000)

    # Pipeline for atomicity + performance
    pipe = r.pipeline()
    # 1. Remove entries older than the window
    pipe.zremrangebyscore(redis_key, 0, window_start_ms)
    # 2. Count remaining entries
    pipe.zcard(redis_key)
    results = pipe.execute()

    current_count = results[1]

    if current_count < max_requests:
        # Allow — add this request to the sorted set
        member = f"{now_ms}-{identifier}"
        r.zadd(redis_key, {member: now_ms})
        r.expire(redis_key, window_seconds + 1)

        allowed = True
        remaining = max_requests - current_count - 1
        retry_after = 0.0
    else:
        # Blocked — find the oldest entry to tell caller when to retry
        oldest = r.zrange(redis_key, 0, 0, withscores=True)
        if oldest:
            oldest_score_ms = oldest[0][1]
            retry_after = round(((oldest_score_ms + window_seconds * 1000) - now_ms) / 1000, 2)
        else:
            retry_after = window_seconds

        allowed = False
        remaining = 0

    result = {
        "allowed": allowed,
        "remaining": max(0, remaining if allowed else 0),
        "limit": max_requests,
        "algorithm": "sliding_window",
    }
    if not allowed:
        result["retry_after"] = max(0.0, retry_after)

    return result


# ---------------------------------------------------------------------------
# Metrics tracking
# ---------------------------------------------------------------------------

def track_metrics(r: Redis, identifier: str, allowed: bool) -> None:
    """
    Increment Redis counters after every rate-limit decision.

    Keys
    ----
    metrics:total_requests          – global total
    metrics:blocked_requests        – global blocked count
    metrics:user:<identifier>:total   – per-user total
    metrics:user:<identifier>:blocked – per-user blocked count
    metrics:history                 – list of JSON snapshots (last 100)
    """
    pipe = r.pipeline()
    pipe.incr("metrics:total_requests")
    pipe.incr(f"metrics:user:{identifier}:total")

    if not allowed:
        pipe.incr("metrics:blocked_requests")
        pipe.incr(f"metrics:user:{identifier}:blocked")

    pipe.execute()

    # --- Append a lightweight history snapshot ---
    snapshot = {
        "timestamp": int(time.time()),
        "total": int(r.get("metrics:total_requests") or 0),
        "blocked": int(r.get("metrics:blocked_requests") or 0),
    }
    r.lpush("metrics:history", json.dumps(snapshot))
    r.ltrim("metrics:history", 0, 99)   # keep only the last 100 snapshots
