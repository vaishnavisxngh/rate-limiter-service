# ⚡ Distributed Rate Limiter Service

A production-grade distributed rate limiting service with **Token Bucket** and **Sliding Window** algorithms, backed by Redis for shared state across multiple instances — with a live React dashboard.

[![CI Pipeline](https://github.com/YOUR_USERNAME/rate-limiter-service/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/rate-limiter-service/actions)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![React](https://img.shields.io/badge/React-18-61DAFB)
![Redis](https://img.shields.io/badge/Redis-7-red)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-MIT-yellow)

> **Live Demo:** [https://your-app.vercel.app](https://your-app.vercel.app)

---

## What is this?

A **rate limiter** controls how many requests a user can make to an API in a given time window — the same technology Amazon, Google, and Stripe use to protect their APIs from abuse and ensure fair usage.

This project implements the rate limiter as a **standalone distributed service** where:
- Multiple FastAPI instances enforce the same limits via shared Redis state
- A real-time React dashboard shows live metrics and lets you manage users
- Both Token Bucket and Sliding Window algorithms are implemented and comparable

---

## Features

- 🔒 **Two algorithms** — Token Bucket (burst-friendly) and Sliding Window (precise)
- 🌐 **Distributed** — multiple instances share state via Redis; limits hold across all of them
- 📊 **Live dashboard** — React UI polling every 2 s with charts, per-user stats, admin controls
- 🧪 **Fully tested** — 15 pytest unit tests covering all core logic
- 🐳 **Dockerized** — one command (`docker-compose up`) starts the entire stack
- 🔄 **CI/CD** — GitHub Actions runs tests and builds Docker images on every push
- 🚀 **Deployed** — backend on Render, frontend on Vercel, Redis on Railway

---

## Architecture

```
API Clients / React Dashboard
          │
          ▼
  ┌───────────────┐      ┌───────────────┐
  │  FastAPI      │      │  FastAPI      │
  │  Instance 1   │◄────►│  Instance 2   │
  │  :8001        │      │  :8002        │
  └──────┬────────┘      └───────┬───────┘
         │                       │
         └──────────┬────────────┘
                    ▼
             ┌─────────────┐
             │    Redis     │  ← Shared state
             │  (single     │     all counters live here
             │   source of  │     so limits are enforced
             │   truth)     │     across every instance
             └─────────────┘
```

Both instances point to the **same Redis container**. A user who uses 8 of their 10 allowed requests on Instance 1 only gets 2 more on Instance 2. That shared enforcement is what makes this "distributed."

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11, FastAPI, Redis (redis-py), python-dotenv |
| **Algorithms** | Token Bucket, Sliding Window (Redis Sorted Sets) |
| **Frontend** | React 18, Vite, TailwindCSS, Recharts, Framer Motion, Lucide |
| **Testing** | Pytest, fakeredis, httpx (FastAPI TestClient) |
| **DevOps** | Docker, Docker Compose, Nginx, GitHub Actions |
| **Deployment** | Render (backend), Vercel (frontend), Railway (Redis) |

---

## Quick Start (Local with Docker)

**Prerequisites:** Docker Desktop, Git

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/rate-limiter-service.git
cd rate-limiter-service

# 2. Start the entire stack (Redis + 2 backend instances + frontend)
docker-compose up --build

# 3. Open the dashboard
open http://localhost:3000
```

That's it. The dashboard will be live at `http://localhost:3000`.

- Backend Instance 1: `http://localhost:8001`
- Backend Instance 2: `http://localhost:8002`
- API docs (Swagger): `http://localhost:8001/docs`

---

## Running Tests

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
pytest tests/ -v
```

All 15 tests should pass. No real Redis required — fakeredis handles it.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check + instance ID |
| `GET` | `/api/data` | Rate-limited endpoint (Token Bucket) |
| `GET` | `/api/data/sliding` | Rate-limited endpoint (Sliding Window) |
| `GET` | `/metrics` | Full metrics snapshot |
| `GET` | `/metrics/live` | Metrics + server timestamp |
| `GET` | `/metrics/history` | Last 100 metric snapshots (for charts) |
| `GET` | `/admin/config` | Get current configuration |
| `POST` | `/admin/config` | Update rate limit parameters |
| `POST` | `/admin/reset/{id}` | Reset a specific user |
| `DELETE` | `/admin/reset-all` | Wipe all data |

**Rate limit response headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
Retry-After: 30        (only on 429 responses)
```

---

## The Distributed Test

To verify that limits are truly shared across instances:

```bash
# Send 8 requests to Instance 1
for i in {1..8}; do curl http://localhost:8001/api/data; done

# Now try Instance 2 — you only get 2 more before 429
for i in {1..5}; do curl http://localhost:8002/api/data; done
```

Instance 2 will start returning `429 Too Many Requests` after 2 successful responses because the counter lives in Redis, not in each instance's memory.

---

## Load Test Results

Tested with Locust (`locust -f locustfile.py --host=http://localhost:8001`):

| Users | Spawn Rate | Requests/sec | Block Rate |
|-------|-----------|--------------|------------|
| 10 | 2/s | ~18 req/s | ~45% |
| 100 | 10/s | ~180 req/s | ~78% |
| 1000 | 50/s | ~850 req/s | ~91% |

High block rates at scale are **expected and correct** — they prove the rate limiter is working.

---

## Project Structure

```
rate-limiter-service/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── redis_client.py      # Redis connection singleton
│   ├── limiter.py           # Token Bucket + Sliding Window algorithms
│   ├── routes/
│   │   ├── rate_limit.py    # /api/data endpoints
│   │   ├── metrics.py       # /metrics endpoints
│   │   └── admin.py         # /admin endpoints
│   ├── tests/
│   │   ├── test_limiter.py  # Algorithm unit tests
│   │   └── test_routes.py   # API integration tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Root component + data fetching loop
│   │   ├── components/
│   │   │   ├── Header.jsx   # Nav + live status + instance switcher
│   │   │   ├── StatsBar.jsx # 4 summary cards
│   │   │   ├── LiveChart.jsx# Recharts line chart
│   │   │   ├── UsersTable.jsx # Per-IP breakdown table
│   │   │   ├── AdminPanel.jsx # Config + danger zone
│   │   │   └── TestPanel.jsx  # Interview demo tool
│   │   └── services/
│   │       └── api.js       # All axios calls in one place
│   ├── Dockerfile
│   └── nginx.conf
├── .github/workflows/ci.yml # GitHub Actions CI pipeline
├── docker-compose.yml       # Full stack orchestration
├── locustfile.py            # Load testing scenarios
└── README.md
```

---

## What I Learned

Building this taught me why distributed systems need a shared external state store — you can't use in-process memory when you have multiple servers. Redis's atomic INCR, ZADD, and EXPIRE operations make the rate limiter both correct and fast. Using Docker Compose to simulate two independent instances on the same machine was the clearest way to prove the distributed property actually works.

---

## License

MIT
