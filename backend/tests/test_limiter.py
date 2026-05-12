"""
Unit tests for the token bucket and sliding window algorithms.
Uses fakeredis so no real Redis instance is required to run the tests.
This is what GitHub Actions will execute on every push.
"""

import pytest
import fakeredis  # type: ignore[import]

# Import the functions we are testing
from limiter import token_bucket_check, sliding_window_check, track_metrics

# Fixtures — reusable test helpers

@pytest.fixture
def r():
    """
    Return a fresh in-memory fakeredis client for each test.
    Each test gets a clean slate with no leftover keys.
    """
    return fakeredis.FakeRedis(decode_responses=True)


TEST_IP = "192.168.1.1"
MAX_TOKENS = 5        # small number so tests run fast
REFILL_RATE = 0.01    # very slow refill so tokens don't come back mid-test

# Token Bucket tests

class TestTokenBucket:

    def test_first_request_is_allowed(self, r):
        """A brand-new IP should always be allowed on its first request."""
        result = token_bucket_check(r, TEST_IP, max_tokens=MAX_TOKENS, refill_rate=REFILL_RATE)

        assert result["allowed"] is True
        assert result["remaining"] == MAX_TOKENS - 1
        assert result["limit"] == MAX_TOKENS
        assert result["algorithm"] == "token_bucket"

    def test_allows_requests_up_to_limit(self, r):
        """Should allow exactly max_tokens requests before blocking."""
        for i in range(MAX_TOKENS):
            result = token_bucket_check(r, TEST_IP, max_tokens=MAX_TOKENS, refill_rate=REFILL_RATE)
            assert result["allowed"] is True, f"Request {i+1} should have been allowed"

    def test_blocks_after_limit_exceeded(self, r):
        """The (max_tokens + 1)th request must be blocked."""
        # Exhaust the bucket
        for _ in range(MAX_TOKENS):
            token_bucket_check(r, TEST_IP, max_tokens=MAX_TOKENS, refill_rate=REFILL_RATE)

        # This one should be blocked
        result = token_bucket_check(r, TEST_IP, max_tokens=MAX_TOKENS, refill_rate=REFILL_RATE)

        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert "retry_after" in result
        assert result["retry_after"] > 0

    def test_different_ips_have_independent_buckets(self, r):
        """Rate limit for IP A must not affect IP B."""
        ip_a = "10.0.0.1"
        ip_b = "10.0.0.2"

        # Exhaust IP A
        for _ in range(MAX_TOKENS):
            token_bucket_check(r, ip_a, max_tokens=MAX_TOKENS, refill_rate=REFILL_RATE)

        # IP B should still be allowed
        result_b = token_bucket_check(r, ip_b, max_tokens=MAX_TOKENS, refill_rate=REFILL_RATE)
        assert result_b["allowed"] is True

    def test_remaining_decrements_correctly(self, r):
        """remaining should decrease by 1 with each successive request."""
        previous_remaining = MAX_TOKENS

        for _ in range(MAX_TOKENS):
            result = token_bucket_check(r, TEST_IP, max_tokens=MAX_TOKENS, refill_rate=REFILL_RATE)
            assert result["remaining"] == previous_remaining - 1
            previous_remaining = result["remaining"]

# Sliding Window tests

class TestSlidingWindow:

    def test_first_request_is_allowed(self, r):
        """A brand-new IP should be allowed on its first request."""
        result = sliding_window_check(r, TEST_IP, max_requests=MAX_TOKENS, window_seconds=60)

        assert result["allowed"] is True
        assert result["algorithm"] == "sliding_window"

    def test_allows_up_to_max_requests(self, r):
        """Should allow exactly max_requests requests in the window."""
        for i in range(MAX_TOKENS):
            result = sliding_window_check(r, TEST_IP, max_requests=MAX_TOKENS, window_seconds=60)
            assert result["allowed"] is True, f"Request {i+1} should have been allowed"

    def test_blocks_when_limit_reached(self, r):
        """Request number max_requests + 1 must be blocked."""
        for _ in range(MAX_TOKENS):
            sliding_window_check(r, TEST_IP, max_requests=MAX_TOKENS, window_seconds=60)

        result = sliding_window_check(r, TEST_IP, max_requests=MAX_TOKENS, window_seconds=60)

        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert "retry_after" in result

    def test_different_ips_independent(self, r):
        """IP A being blocked must not affect IP B."""
        ip_a = "10.0.0.1"
        ip_b = "10.0.0.2"

        for _ in range(MAX_TOKENS):
            sliding_window_check(r, ip_a, max_requests=MAX_TOKENS, window_seconds=60)

        result_b = sliding_window_check(r, ip_b, max_requests=MAX_TOKENS, window_seconds=60)
        assert result_b["allowed"] is True

# Metrics tests

class TestMetrics:

    def test_total_requests_increments(self, r):
        """track_metrics must increment the global total counter."""
        track_metrics(r, TEST_IP, allowed=True)
        track_metrics(r, TEST_IP, allowed=True)
        track_metrics(r, TEST_IP, allowed=True)

        total = int(r.get("metrics:total_requests") or 0)
        assert total == 3

    def test_blocked_requests_increments_only_when_blocked(self, r):
        """Blocked counter must only go up when allowed=False."""
        track_metrics(r, TEST_IP, allowed=True)
        track_metrics(r, TEST_IP, allowed=False)
        track_metrics(r, TEST_IP, allowed=True)
        track_metrics(r, TEST_IP, allowed=False)

        blocked = int(r.get("metrics:blocked_requests") or 0)
        assert blocked == 2

    def test_per_user_counters_tracked(self, r):
        """Per-user total and blocked counters must be correct."""
        ip = "172.16.0.1"
        track_metrics(r, ip, allowed=True)
        track_metrics(r, ip, allowed=True)
        track_metrics(r, ip, allowed=False)

        user_total = int(r.get(f"metrics:user:{ip}:total") or 0)
        user_blocked = int(r.get(f"metrics:user:{ip}:blocked") or 0)

        assert user_total == 3
        assert user_blocked == 1

    def test_history_is_recorded(self, r):
        """Each call to track_metrics should add an entry to metrics:history."""
        track_metrics(r, TEST_IP, allowed=True)
        track_metrics(r, TEST_IP, allowed=False)

        history_length = r.llen("metrics:history")
        assert history_length == 2
