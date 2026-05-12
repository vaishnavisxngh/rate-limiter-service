"""
routes/metrics.py
~~~~~~~~~~~~~~~~~
Read-only endpoints that expose what is happening inside the rate limiter.

GET  /metrics        – snapshot of all counters right now
GET  /metrics/live   – same snapshot + timestamp  (polled by the dashboard)
GET  /metrics/history – last 100 snapshots as a list  (used by the chart)
"""

import time
import json
from fastapi import APIRouter
from redis_client import get_redis

router = APIRouter(tags=["Metrics"])


def _build_metrics(r) -> dict:
    """
    Collect all metrics from Redis and return them as a plain dict.
    Extracted into its own function so both /metrics and /metrics/live
    can reuse the same logic without duplication.
    """
    total = int(r.get("metrics:total_requests") or 0)
    blocked = int(r.get("metrics:blocked_requests") or 0)
    allowed = total - blocked
    block_rate = round((blocked / total * 100), 2) if total > 0 else 0.0

    # Per-user breakdown
    # Find every key that looks like  metrics:user:<ip>:total
    user_total_keys = r.keys("metrics:user:*:total")
    users = []

    for key in user_total_keys:
        # key format: metrics:user:<identifier>:total
        parts = key.split(":")
        # parts = ["metrics", "user", "<identifier>", "total"]
        identifier = parts[2]

        user_total = int(r.get(key) or 0)
        user_blocked = int(r.get(f"metrics:user:{identifier}:blocked") or 0)

        # Fetch current token state from the token bucket key
        bucket = r.hgetall(f"token_bucket:{identifier}")
        tokens_remaining = round(float(bucket.get("tokens", 0)), 1) if bucket else 0

        # A user is currently "blocked" if their bucket is empty
        is_blocked = tokens_remaining < 1

        users.append({
            "identifier": identifier,
            "total_requests": user_total,
            "blocked_requests": user_blocked,
            "tokens_remaining": tokens_remaining,
            "status": "BLOCKED" if is_blocked else "ALLOWED",
        })

    # Sort by total requests descending so busiest users appear first
    users.sort(key=lambda u: u["total_requests"], reverse=True)

    return {
        "total_requests": total,
        "blocked_requests": blocked,
        "allowed_requests": allowed,
        "block_rate_percent": block_rate,
        "active_users": len(users),
        "users": users,
    }

# Routes

@router.get("/metrics")
async def get_metrics():
    """Full metrics snapshot."""
    r = get_redis()
    return _build_metrics(r)

@router.get("/metrics/live")
async def get_metrics_live():
    """
    Same as /metrics but adds a server timestamp.
    The React dashboard calls this every 2 seconds.
    """
    r = get_redis()
    data = _build_metrics(r)
    data["server_timestamp"] = time.time()
    return data

@router.get("/metrics/history")
async def get_metrics_history():
    """
    Returns the last 100 metric snapshots as a list, newest first.
    Each snapshot is a dict with keys: timestamp, total, blocked.
    The React line chart uses this list as its data source.
    """
    r = get_redis()
    raw_list = r.lrange("metrics:history", 0, -1)   # newest first (LPUSH)

    history = []
    for raw in raw_list:
        try:
            history.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            continue   # skip malformed entries

    # Reverse so the chart gets chronological order (oldest → newest)
    history.reverse()
    return {"history": history, "count": len(history)}