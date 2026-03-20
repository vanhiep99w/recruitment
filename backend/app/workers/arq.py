"""
ARQ worker configuration.

Run as a separate process:
    arq app.workers.arq.WorkerSettings

Queues:
    - default: general background tasks
    - cv_parsing: CV text extraction + profile parsing
    - matching: candidate–job matching scoring
    - jd_analysis: JD text analysis + embedding generation
"""
from __future__ import annotations

from arq.connections import RedisSettings

from app.config import settings


# ---------------------------------------------------------------------------
# Helper: parse REDIS_URL into arq.connections.RedisSettings
# ---------------------------------------------------------------------------
def _redis_settings_from_url(url: str) -> RedisSettings:
    """Convert a redis:// URL string into an ARQ RedisSettings instance."""
    # arq.connections.RedisSettings.from_dsn was added in arq 0.25
    try:
        return RedisSettings.from_dsn(url)
    except AttributeError:
        # Fallback: parse manually for older arq versions
        import urllib.parse as _up
        parsed = _up.urlparse(url)
        db = int((parsed.path or "/0").lstrip("/") or 0)
        return RedisSettings(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=parsed.password,
            database=db,
        )


# ---------------------------------------------------------------------------
# Task functions — stubs; implementations live in feature tasks
# ---------------------------------------------------------------------------
async def parse_cv(ctx: dict, cv_id: str) -> dict:
    """Parse a CV file and extract structured profile data."""
    # Implementation provided by recruitment-5h9.x CV parsing task
    raise NotImplementedError(f"parse_cv not yet implemented (cv_id={cv_id})")


async def analyze_jd(ctx: dict, job_id: str) -> dict:
    """Analyse a job description and build a JDProfile."""
    raise NotImplementedError(f"analyze_jd not yet implemented (job_id={job_id})")


async def score_match(ctx: dict, candidate_id: str, job_id: str) -> dict:
    """Compute match score between a candidate and a job."""
    raise NotImplementedError(
        f"score_match not yet implemented (candidate_id={candidate_id}, job_id={job_id})"
    )


# ---------------------------------------------------------------------------
# ARQ WorkerSettings
# ---------------------------------------------------------------------------
class WorkerSettings:
    """
    ARQ worker settings class.
    Run with:  arq app.workers.arq.WorkerSettings
    """

    # Redis connection
    redis_settings: RedisSettings = _redis_settings_from_url(settings.REDIS_URL)

    # Registered task functions
    functions: list = [parse_cv, analyze_jd, score_match]

    # Primary queue name
    queue_name: str = "arq:default"

    # Worker concurrency
    max_jobs: int = 10

    # Job timeout (seconds)
    job_timeout: int = 300

    # Keep result TTL (seconds) — 24 hours
    keep_result: int = 86400

    # Health check interval
    health_check_interval: int = 30

    @classmethod
    async def on_startup(cls, ctx: dict) -> None:
        """Called when the worker starts — set up shared resources."""
        from app.database import AsyncSessionLocal
        from app.services.llm_client import LLMClient

        ctx["db_session_factory"] = AsyncSessionLocal
        ctx["llm_client"] = LLMClient()

    @classmethod
    async def on_shutdown(cls, ctx: dict) -> None:
        """Called when the worker shuts down — clean up resources."""
        llm_client = ctx.get("llm_client")
        if llm_client is not None:
            await llm_client.close()
