"""
Load test for the Distributed Rate Limiter Service.


# Install: pip install locust

# Run against local Docker Compose stack:
locust -f locustfile.py --host=http://localhost:8001

# Then open http://localhost:8089 in your browser.
# Set number of users and spawn rate in the UI.

Recommended test runs
---------------------
Test 1: 10 users,   spawn rate 2/s  → warm-up / baseline
Test 2: 100 users,  spawn rate 10/s → moderate load
Test 3: 1000 users, spawn rate 50/s → stress test (this is your resume number)
"""

from locust import HttpUser, task, between  # type: ignore[import]


class RateLimiterUser(HttpUser):
    """
    Simulates a single user interacting with the rate limiter API.

    wait_time defines how long each simulated user pauses between tasks.
    between(0.1, 0.5) → random wait of 100–500 ms, meaning each user
    sends 2–10 requests per second.
    """
    wait_time = between(0.1, 0.5)

    # Tasks
    # The number in @task(N) is the relative weight — how often this task
    # is chosen compared to others.  @task(3) runs ~3× more than @task(1).

    @task(3)
    def hit_token_bucket(self):
        """
        Most common task — hammer the Token Bucket endpoint.
        Weight 3 means 60 % of requests go here.
        """
        with self.client.get("/api/data", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # 429 is EXPECTED behaviour — mark as success so Locust
                # doesn't count it as a failure in the error report.
                response.failure("Rate limited (429)") #still counts as failure in stats, but we want to see it in the report
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def hit_sliding_window(self):
        """
        Hit the Sliding Window endpoint.
        Weight 2 → ~40 % of requests.
        """
        with self.client.get("/api/data/sliding", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited (429)")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def check_metrics(self):
        """
        Periodically poll the metrics endpoint — simulates the dashboard.
        Weight 1 → ~20 % of requests.
        """
        with self.client.get("/metrics/live", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics endpoint failed: {response.status_code}")

    def on_start(self):
        """Called once when each simulated user starts. Optional warm-up."""
        self.client.get("/health")
