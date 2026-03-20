"""
Tests for ARQ worker configuration — verifies queue setup and Redis config.
Phase 1: RED — these tests must fail before implementation.
"""
import uuid

import pytest
from unittest.mock import AsyncMock, patch


def test_arq_worker_settings_importable():
    """WorkerSettings must be importable from app.workers.arq."""
    from app.workers.arq import WorkerSettings
    assert WorkerSettings is not None


def test_arq_worker_settings_has_redis_settings():
    """WorkerSettings must have redis_settings attribute."""
    from app.workers.arq import WorkerSettings
    assert hasattr(WorkerSettings, "redis_settings")


def test_arq_worker_settings_has_functions():
    """WorkerSettings must have functions list."""
    from app.workers.arq import WorkerSettings
    assert hasattr(WorkerSettings, "functions")
    assert isinstance(WorkerSettings.functions, (list, tuple))


def test_arq_worker_settings_has_queue_name():
    """WorkerSettings must define a queue name."""
    from app.workers.arq import WorkerSettings
    assert hasattr(WorkerSettings, "queue_name")


def test_workers_package_importable():
    """app.workers package must be importable."""
    import app.workers
    assert app.workers is not None


def test_arq_redis_settings_from_config():
    """ARQ redis_settings must use REDIS_URL from config."""
    from app.workers.arq import WorkerSettings
    from arq.connections import RedisSettings
    assert isinstance(WorkerSettings.redis_settings, RedisSettings)


# ---------------------------------------------------------------------------
# Additional tests for uncovered lines
# ---------------------------------------------------------------------------

def test_worker_settings_max_jobs():
    """WorkerSettings.max_jobs should be a positive integer."""
    from app.workers.arq import WorkerSettings
    assert isinstance(WorkerSettings.max_jobs, int)
    assert WorkerSettings.max_jobs > 0


def test_worker_settings_job_timeout():
    """WorkerSettings.job_timeout should be set."""
    from app.workers.arq import WorkerSettings
    assert isinstance(WorkerSettings.job_timeout, int)
    assert WorkerSettings.job_timeout > 0


def test_worker_settings_keep_result():
    """WorkerSettings.keep_result should be set."""
    from app.workers.arq import WorkerSettings
    assert isinstance(WorkerSettings.keep_result, int)


def test_worker_settings_health_check_interval():
    """WorkerSettings.health_check_interval should be set."""
    from app.workers.arq import WorkerSettings
    assert isinstance(WorkerSettings.health_check_interval, int)


def test_worker_settings_functions_contain_tasks():
    """WorkerSettings.functions must include parse_cv, analyze_jd, score_match."""
    from app.workers.arq import WorkerSettings, parse_cv, analyze_jd, score_match
    assert parse_cv in WorkerSettings.functions
    assert analyze_jd in WorkerSettings.functions
    assert score_match in WorkerSettings.functions


def test_parse_cv_raises_not_implemented():
    """parse_cv must raise NotImplementedError."""
    import asyncio
    from app.workers.arq import parse_cv
    with pytest.raises(NotImplementedError, match="parse_cv"):
        asyncio.run(parse_cv({}, "cv-123"))


def test_analyze_jd_raises_not_implemented():
    """analyze_jd must raise NotImplementedError."""
    import asyncio
    from app.workers.arq import analyze_jd
    with pytest.raises(NotImplementedError, match="analyze_jd"):
        asyncio.run(analyze_jd({}, "job-123"))


def test_score_match_raises_not_implemented():
    """score_match must raise NotImplementedError."""
    import asyncio
    from app.workers.arq import score_match
    with pytest.raises(NotImplementedError, match="score_match"):
        asyncio.run(score_match({}, "cand-1", "job-1"))


@pytest.mark.asyncio
async def test_on_startup_sets_context():
    """on_startup must populate ctx with db_session_factory and llm_client."""
    from unittest.mock import MagicMock
    from app.workers.arq import WorkerSettings

    mock_session_factory = MagicMock()
    mock_llm_client_class = MagicMock()
    mock_llm_instance = MagicMock()
    mock_llm_client_class.return_value = mock_llm_instance

    ctx: dict = {}
    with patch("app.workers.arq.AsyncSessionLocal" if False else "app.database.AsyncSessionLocal", mock_session_factory):
        with patch("app.services.llm_client.LLMClient", mock_llm_client_class):
            # Patch directly inside the on_startup imports
            with patch.dict("sys.modules", {}):
                import app.database as db_mod
                import app.services.llm_client as llm_mod
                original_session = db_mod.AsyncSessionLocal
                original_llm = llm_mod.LLMClient
                db_mod.AsyncSessionLocal = mock_session_factory
                llm_mod.LLMClient = mock_llm_client_class
                try:
                    await WorkerSettings.on_startup(ctx)
                finally:
                    db_mod.AsyncSessionLocal = original_session
                    llm_mod.LLMClient = original_llm

    assert "db_session_factory" in ctx
    assert "llm_client" in ctx


@pytest.mark.asyncio
async def test_on_shutdown_calls_llm_close():
    """on_shutdown must call llm_client.close() if present in ctx."""
    from unittest.mock import AsyncMock
    from app.workers.arq import WorkerSettings

    mock_llm = AsyncMock()
    ctx = {"llm_client": mock_llm}
    await WorkerSettings.on_shutdown(ctx)
    mock_llm.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_shutdown_no_llm_client_noop():
    """on_shutdown must not fail when llm_client is absent from ctx."""
    from app.workers.arq import WorkerSettings
    ctx: dict = {}
    # Should not raise
    await WorkerSettings.on_shutdown(ctx)


def test_redis_settings_from_url_fallback():
    """_redis_settings_from_url must work even if from_dsn is unavailable."""
    from app.workers import arq as arq_module
    from arq.connections import RedisSettings
    from unittest.mock import MagicMock

    # Simulate AttributeError on from_dsn (older arq version fallback)
    mock_redis_settings_class = MagicMock(spec=RedisSettings)
    mock_redis_settings_class.from_dsn.side_effect = AttributeError("no from_dsn")
    mock_instance = MagicMock(spec=RedisSettings)
    mock_redis_settings_class.return_value = mock_instance

    with patch("app.workers.arq.RedisSettings", mock_redis_settings_class):
        result = arq_module._redis_settings_from_url("redis://localhost:6379/0")

    mock_redis_settings_class.assert_called_once_with(
        host="localhost",
        port=6379,
        password=None,
        database=0,
    )


@pytest.mark.asyncio
async def test_process_cv_job_removes_temp_file(tmp_path):
    """process_cv_job removes the temporary upload file after processing."""
    from app.workers.arq import process_cv_job

    temp_file = tmp_path / "resume.pdf"
    temp_file.write_text("temporary cv content")

    mock_llm = type(
        "MockLLM",
        (),
        {
            "parse_cv": staticmethod(
                AsyncMock(return_value={"name": "Jane", "skills": [], "experience": [], "education": []})
            )
        },
    )()

    with patch("app.services.document_extractor.extract", return_value=("Jane CV", 1.0)):
        result = await process_cv_job(
            {"llm_client": mock_llm, "redis": None, "db_session_factory": None},
            str(temp_file),
            ".pdf",
        )

    assert result["status"] == "complete"
    assert not temp_file.exists()


@pytest.mark.asyncio
async def test_process_cv_job_returns_existing_candidate_for_duplicate(tmp_path):
    """Duplicate CVs should reuse the existing candidate instead of creating a new one."""
    from app.workers.arq import process_cv_job

    temp_file = tmp_path / "resume.pdf"
    temp_file.write_text("temporary cv content")

    existing_id = uuid.uuid4()
    existing_candidate = type("ExistingCandidate", (), {"id": existing_id})()

    class FakeSession:
        def __init__(self):
            self.added = []
            self.flush_calls = 0
            self.commit_calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            self.flush_calls += 1

        async def commit(self):
            self.commit_calls += 1

    fake_session = FakeSession()

    class FakeSessionFactory:
        def __call__(self):
            return fake_session

    mock_llm = type(
        "MockLLM",
        (),
        {
            "parse_cv": staticmethod(
                AsyncMock(
                    return_value={"name": "Jane Doe", "email": "jane@example.com", "skills": [], "experience": [], "education": []}
                )
            )
        },
    )()

    with (
        patch("app.services.document_extractor.extract", return_value=("Jane CV", 1.0)),
        patch("app.services.duplicate_detection.find_duplicate_candidate", AsyncMock(return_value=existing_candidate)),
    ):
        result = await process_cv_job(
            {"llm_client": mock_llm, "redis": None, "db_session_factory": FakeSessionFactory()},
            str(temp_file),
            ".pdf",
            org_id=str(uuid.uuid4()),
        )

    assert result["status"] == "complete"
    assert result["candidate_id"] == str(existing_id)
    assert result["duplicate"] is True
    assert result["existing_id"] == str(existing_id)
    assert fake_session.commit_calls == 1
    assert fake_session.flush_calls == 0
    assert [type(obj).__name__ for obj in fake_session.added] == ["CV"]
