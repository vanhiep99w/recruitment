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

import json

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
# Task functions
# ---------------------------------------------------------------------------

async def _update_progress(
    redis, batch_job_id: str, index: int, result: dict
) -> None:
    """Write per-file progress to Redis (best-effort)."""
    if redis is None:
        return
    key = f"cv_job:{batch_job_id}:{index}"
    await redis.set(key, json.dumps(result), ex=3600)


async def process_cv_job(
    ctx: dict,
    file_path: str,
    file_type: str,
    user_id: str | None = None,
    org_id: str | None = None,
    batch_job_id: str | None = None,
    file_index: int = 0,
) -> dict:
    """
    Process a single CV file: extract text, parse with LLM, save to DB.

    Args:
        ctx:           ARQ worker context (contains db_session_factory, llm_client).
        file_path:     Absolute path to the saved CV file.
        file_type:     File extension, e.g. ".pdf", ".docx".
        user_id:       Optional uploading user ID.
        org_id:        Required organisation ID for the Candidate record.
        batch_job_id:  Shared batch job ID used as Redis key prefix.
        file_index:    Index of this file within the batch.

    Returns:
        A dict summarising the result: {status, candidate_id, error}.
    """
    import uuid as _uuid
    from pathlib import Path as _Path

    # Resolve batch_job_id — fall back to a generated UUID if not provided
    effective_batch_id: str = batch_job_id or str(_uuid.uuid4())

    redis = ctx.get("redis")
    file_to_cleanup = _Path(file_path)

    try:
        from app.services.document_extractor import extract

        text, confidence = extract(file_to_cleanup, file_type)

        # Normalize confidence to 0-100 scale.
        # document_extractor returns 1.0 for text-based extraction and
        # 0-100 for OCR-based extraction.  Values <= 1.0 are on the 0-1
        # scale and must be multiplied by 100 before comparing with the
        # 0-100 threshold.
        confidence_pct = confidence * 100.0 if confidence <= 1.0 else confidence

        llm_client = ctx.get("llm_client")
        if llm_client is None:
            from app.services.llm_client import LLMClient
            llm_client = LLMClient()

        parsed = await llm_client.parse_cv(text)

        # Persist to DB
        db_session_factory = ctx.get("db_session_factory")
        candidate_id: str | None = None

        if db_session_factory is not None:
            from datetime import datetime, timezone
            import uuid as _uuid2

            from app.models.candidate import Candidate
            from app.models.candidate_profile import CandidateProfile
            from app.models.cv import CV
            from app.services.duplicate_detection import find_duplicate_candidate

            async with db_session_factory() as session:
                effective_org_id = _uuid2.UUID(org_id) if org_id else _uuid2.uuid4()
                duplicate_candidate = await find_duplicate_candidate(
                    session=session,
                    org_id=effective_org_id,
                    name=parsed.get("name"),
                    email=parsed.get("email"),
                )

                parse_status = "ocr_low_quality" if confidence_pct < 60.0 else "parsed"

                if duplicate_candidate is not None:
                    cv_record = CV(
                        candidate_id=duplicate_candidate.id,
                        file_url=file_path,
                        file_type=file_type.lstrip("."),
                        parse_status=parse_status,
                        raw_text=text,
                    )
                    session.add(cv_record)
                    await session.commit()
                    candidate_id = str(duplicate_candidate.id)

                    per_file_result = {
                        "filename": file_path,
                        "status": "complete",
                        "error": None,
                        "duplicate": True,
                        "existing_id": candidate_id,
                    }
                    await _update_progress(redis, effective_batch_id, file_index, per_file_result)

                    return {
                        "status": "complete",
                        "candidate_id": candidate_id,
                        "confidence": confidence,
                        "error": None,
                        "duplicate": True,
                        "existing_id": candidate_id,
                    }

                candidate = Candidate(
                    name=parsed.get("name") or "Unknown",
                    email=parsed.get("email") or None,
                    phone=parsed.get("phone") or None,
                    org_id=effective_org_id,
                )
                session.add(candidate)
                await session.flush()

                profile = CandidateProfile(
                    candidate_id=candidate.id,
                    skills=parsed.get("skills") or [],
                    work_experience={"entries": parsed.get("experience") or []},
                    education={"entries": parsed.get("education") or []},
                    parse_status=parse_status,
                    parsed_at=datetime.now(timezone.utc),
                )
                session.add(profile)

                cv_record = CV(
                    candidate_id=candidate.id,
                    file_url=file_path,
                    file_type=file_type.lstrip("."),
                    parse_status=parse_status,
                    raw_text=text,
                )
                session.add(cv_record)

                await session.commit()
                candidate_id = str(candidate.id)

        per_file_result = {
            "filename": file_path,
            "status": "complete",
            "error": None,
        }
        await _update_progress(redis, effective_batch_id, file_index, per_file_result)

        return {
            "status": "complete",
            "candidate_id": candidate_id,
            "confidence": confidence,
            "error": None,
        }

    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)
        per_file_result = {
            "filename": file_path,
            "status": "failed",
            "error": error_msg,
        }
        await _update_progress(redis, effective_batch_id, file_index, per_file_result)
        return {
            "status": "failed",
            "candidate_id": None,
            "error": error_msg,
        }
    finally:
        try:
            file_to_cleanup.unlink(missing_ok=True)
        except OSError:
            pass


async def parse_cv(ctx: dict, cv_id: str) -> dict:
    """Parse a CV file and extract structured profile data."""
    # Legacy stub — use process_cv_job for new uploads
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
    functions: list = [process_cv_job, parse_cv, analyze_jd, score_match]

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
