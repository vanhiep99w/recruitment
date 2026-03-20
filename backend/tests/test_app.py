"""
Tests for FastAPI app — verifies importability and /health endpoint.
Phase 1: RED — these tests must fail before implementation.
"""
import pytest
from httpx import ASGITransport, AsyncClient


def test_app_importable():
    """FastAPI app must be importable from app.main."""
    from app.main import app
    assert app is not None


def test_app_is_fastapi_instance():
    """app must be a FastAPI instance."""
    from fastapi import FastAPI
    from app.main import app
    assert isinstance(app, FastAPI)


def test_app_has_health_endpoint():
    """App must have a /health route registered."""
    from app.main import app
    routes = {route.path for route in app.routes}
    assert "/health" in routes


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """GET /health must return 200 with status ok."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"


def test_database_module_importable():
    """app.database must be importable."""
    from app import database
    assert database is not None


def test_database_has_async_session_maker():
    """app.database must expose async_session or async_session_maker."""
    import app.database as db
    has_session = (
        hasattr(db, "async_session") or
        hasattr(db, "AsyncSessionLocal") or
        hasattr(db, "get_db")
    )
    assert has_session, "database module must expose async session maker or get_db"


def test_database_has_base():
    """app.database must expose SQLAlchemy declarative Base."""
    import app.database as db
    assert hasattr(db, "Base"), "database module must expose SQLAlchemy Base"
