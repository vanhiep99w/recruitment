"""
Tests for config.py — verifies all required env vars are loaded.
Phase 1: RED — these tests must fail before implementation.
"""
import os
import pytest


def test_config_loads_database_url():
    """Config must load DATABASE_URL from environment."""
    from app.config import settings
    assert settings.DATABASE_URL is not None
    assert "postgresql" in settings.DATABASE_URL


def test_config_loads_redis_url():
    """Config must load REDIS_URL from environment."""
    from app.config import settings
    assert settings.REDIS_URL is not None
    assert "redis" in settings.REDIS_URL


def test_config_loads_llm_base_url():
    """Config must load LLM_BASE_URL from environment."""
    from app.config import settings
    assert settings.LLM_BASE_URL is not None


def test_config_loads_llm_api_key():
    """Config must load LLM_API_KEY from environment."""
    from app.config import settings
    assert settings.LLM_API_KEY is not None


def test_config_loads_jwt_secret():
    """Config must load JWT_SECRET from environment."""
    from app.config import settings
    assert settings.JWT_SECRET is not None


def test_config_has_jwt_algorithm():
    """Config must specify JWT algorithm as HS256."""
    from app.config import settings
    assert settings.JWT_ALGORITHM == "HS256"


def test_config_has_all_required_fields():
    """Config object must expose all required fields."""
    from app.config import settings
    required_fields = ["DATABASE_URL", "REDIS_URL", "LLM_BASE_URL", "LLM_API_KEY", "JWT_SECRET"]
    for field in required_fields:
        assert hasattr(settings, field), f"Settings missing field: {field}"
