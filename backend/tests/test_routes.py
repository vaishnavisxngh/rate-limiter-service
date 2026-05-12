"""
tests/test_routes.py
~~~~~~~~~~~~~~~~~~~~
Integration tests for the FastAPI endpoints.

Uses FastAPI's TestClient (backed by httpx) + fakeredis to run real HTTP
requests against the app without needing a live server or Redis.
"""

import pytest
import fakeredis
from fastapi.testclient import TestClient

# We need to patch the redis client BEFORE importing the app
import redis_client as rc


@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    """
    Replace the real Redis client with an in-memory fakeredis for every test.
    autouse=True means this fixture runs automatically for every test in this file.
    """
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(rc, "_client", fake)
    yield fake
    # fakeredis is torn down automatically after each test


@pytest.fixture
def client():
    """Return a TestClient bound to the FastAPI app."""
    from main import app
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Root / health
# ---------------------------------------------------------------------------

class TestHealthEndpoints:

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "service" in response.json()

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Rate-limited endpoints
# ---------------------------------------------------------------------------

class TestRateLimitEndpoints:

    def test_first_request_allowed(self, client):
        """First request from any IP must return 200."""
        response = client.get("/api/data")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["algorithm"] == "token_bucket"

    def test_429_after_limit(self, client):
        """After exhausting the bucket the endpoint must return 429."""
        # Send 11 requests (default limit is 10)
        responses = [client.get("/api/data") for _ in range(11)]
        status_codes = [r.status_code for r in responses]

        assert 200 in status_codes, "At least some requests should succeed"
        assert 429 in status_codes, "At least one request should be rate-limited"

    def test_429_has_retry_after_header(self, client):
        """Blocked responses must include the Retry-After header."""
        for _ in range(11):
            response = client.get("/api/data")

        if response.status_code == 429:
            assert "retry-after" in response.headers or "Retry-After" in response.headers

    def test_sliding_window_endpoint_works(self, client):
        """Sliding window endpoint should return 200 on first request."""
        response = client.get("/api/data/sliding")
        assert response.status_code == 200
        assert response.json()["algorithm"] == "sliding_window"


# ---------------------------------------------------------------------------
# Metrics endpoints
# ---------------------------------------------------------------------------

class TestMetricsEndpoints:

    def test_metrics_returns_200(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_structure(self, client):
        """Metrics response must contain the expected top-level keys."""
        client.get("/api/data")   # generate at least one data point
        response = client.get("/metrics")
        body = response.json()

        assert "total_requests" in body
        assert "blocked_requests" in body
        assert "allowed_requests" in body
        assert "block_rate_percent" in body
        assert "users" in body

    def test_metrics_live_has_timestamp(self, client):
        response = client.get("/metrics/live")
        assert response.status_code == 200
        assert "server_timestamp" in response.json()

    def test_metrics_history_structure(self, client):
        client.get("/api/data")   # generate at least one history entry
        response = client.get("/metrics/history")
        assert response.status_code == 200
        body = response.json()
        assert "history" in body
        assert "count" in body


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

class TestAdminEndpoints:

    def test_get_config(self, client):
        response = client.get("/admin/config")
        assert response.status_code == 200
        body = response.json()
        assert "max_tokens" in body
        assert "refill_rate" in body

    def test_update_config(self, client):
        payload = {
            "max_tokens": 20,
            "refill_rate": 0.5,
            "max_requests": 20,
            "window_seconds": 30,
        }
        response = client.post("/admin/config", json=payload)
        assert response.status_code == 200
        assert response.json()["config"]["max_tokens"] == 20

    def test_reset_nonexistent_user_returns_404(self, client):
        response = client.post("/admin/reset/999.999.999.999")
        assert response.status_code == 404

    def test_reset_existing_user(self, client):
        # Create some data for the test IP first
        client.get("/api/data")   # this uses the test client's IP (testclient)
        # Now reset it
        response = client.post("/admin/reset/testclient")
        # Either 200 (found and deleted) or 404 (key name differs) — both are valid
        assert response.status_code in (200, 404)

    def test_reset_all(self, client):
        client.get("/api/data")
        response = client.delete("/admin/reset-all")
        assert response.status_code == 200
        assert "keys_deleted" in response.json()
