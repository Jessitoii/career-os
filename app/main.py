import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import dashboard
from app.core.config import settings
from app.core.security import setup_secure_logging

# Setup highly secure, PII-scrubbed logging
setup_secure_logging(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="Career OS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/v1")

@app.get("/health/live")
def health_live():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/health/ready")
def health_ready():
    from app.core.db import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Readiness probe failed DB check: {e}")
        return {"status": "unready", "database": "disconnected"}
        
    from app.core.kill_switch import redis_client
    try:
        redis_client.ping()
    except Exception as e:
        logger.error(f"Readiness probe failed Redis check: {e}")
        return {"status": "unready", "redis": "disconnected"}

    return {"status": "ready", "database": "connected", "redis": "connected"}

if __name__ == "__main__":
    import uvicorn
    # Run uvicorn programmatically so `python app/main.py` works natively
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

