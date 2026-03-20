"""
Test configuration and fixtures for backend tests.
No real DB or Redis connections — uses mocks/stubs.
"""
import os
import pytest


# Set required environment variables before any imports
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/testdb")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("LLM_BASE_URL", "https://api.openai.com/v1")
os.environ.setdefault("LLM_API_KEY", "test-api-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-testing-only")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
