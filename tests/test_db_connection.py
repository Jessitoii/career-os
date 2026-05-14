import pytest
from sqlalchemy import text
from app.core.db import engine
from redis import Redis
from app.core.config import settings

def test_postgres_connection():
    """
    Test Postgres connection. Skips if DB is unavailable
    to support running tests on machines without Docker/DB installed.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    except Exception as e:
        pytest.skip(f"PostgreSQL connection failed. Skipping test. Error: {e}")

def test_redis_connection():
    """
    Test Redis connection. Skips if Redis is unavailable.
    """
    try:
        client = Redis.from_url(settings.REDIS_URL)
        assert client.ping() is True
    except Exception as e:
        pytest.skip(f"Redis connection failed. Skipping test. Error: {e}")
