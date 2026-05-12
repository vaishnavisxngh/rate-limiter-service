"""
FastAPI application entry point.

Responsibilities
1. Create the FastAPI app object.
2. Register CORS middleware so the React dashboard can call the API.
3. Mount all route modules.
4. Expose a root ( / ) and health ( /health ) endpoint.
5. Test the Redis connection on startup.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from redis_client import test_redis_connection
from routes.rate_limit import router as rate_limit_router
from routes.metrics import router as metrics_router
from routes.admin import router as admin_router

# App

app = FastAPI(
    title="Distributed Rate Limiter Service",
    description=(
        "A distributed rate-limiting API with Token Bucket and Sliding Window "
        "algorithms, backed by Redis for shared state across multiple instances."
    ),
    version="1.0.0",
)

# CORS — allow the React dev server and production Vercel URL

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "Retry-After",
    ],
)

# Routers

app.include_router(rate_limit_router)   # /api/data, /api/data/sliding
app.include_router(metrics_router)      # /metrics, /metrics/live, /metrics/history
app.include_router(admin_router)        # /admin/*

# Startup event

@app.on_event("startup")
async def on_startup():
    print("Rate Limiter Service starting …")
    test_redis_connection()
    print(f"Instance ID : {os.getenv('INSTANCE_ID', 'local')}")
    print("Ready.")

# Root endpoints

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Distributed Rate Limiter",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Root"])
async def health():
    """
    Health check endpoint.
    Returns the instance ID so you can verify which container responded.
    """
    return {
        "status": "ok",
        "instance": os.getenv("INSTANCE_ID", "local"),
    }
