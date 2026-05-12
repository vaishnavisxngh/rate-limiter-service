import os
import redis
from dotenv import load_dotenv

load_dotenv()

# Build one shared Redis client from environment variables.
# In Docker, REDIS_HOST will be "redis" (the service name in docker-compose).
# Locally it will be "localhost".

_client: redis.Redis | None = None

def get_redis() -> redis.Redis:
    """Return the shared Redis client, creating it on first call."""
    global _client
    if _client is None:
        _client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True,   # always return str, never bytes
        )
    return _client


def test_redis_connection() -> bool:
    """Ping Redis and print the result. Returns True if healthy."""
    try:
        client = get_redis()
        client.ping()
        print("Redis connection OK")
        return True
    except redis.ConnectionError as exc:
        print(f"Redis connection FAILED: {exc}")
        return False
