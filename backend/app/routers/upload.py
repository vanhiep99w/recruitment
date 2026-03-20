"""
Upload Router — handles CV file uploads (single and ZIP batch).

Endpoints:
    POST /api/upload          — Upload a single CV file or ZIP batch
    GET  /api/upload/{job_id}/status — Check job processing status
"""
from __future__ import annotations

import io
import json
import logging
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/zip",
    "application/x-zip-compressed",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_ZIP_FILES = 200
UPLOAD_DIR = Path("/tmp/uploads")

# ---------------------------------------------------------------------------
# Helpers (can be patched in tests)
# ---------------------------------------------------------------------------

async def enqueue_cv_job(
    file_path: str,
    file_type: str,
    user_id: str | None = None,
    org_id: str | None = None,
    job_id: str | None = None,
    batch_job_id: str | None = None,
    file_index: int = 0,
) -> str:
    """
    Enqueue a CV processing job in ARQ.

    Returns the job_id string. Importing arq lazily so that the module
    can be imported without a live Redis connection.
    """
    from arq import create_pool
    from arq.connections import RedisSettings

    from app.config import settings
    from app.workers.arq import _redis_settings_from_url

    redis = await create_pool(_redis_settings_from_url(settings.REDIS_URL))
    jid = job_id or str(uuid.uuid4())
    effective_batch_id = batch_job_id or jid
    await redis.enqueue_job(
        "process_cv_job",
        file_path,
        file_type,
        user_id,
        org_id,
        effective_batch_id,
        file_index,
        _job_id=jid,
    )
    await redis.close()
    return jid


async def get_job_status(job_id: str) -> dict | None:
    """
    Retrieve job status from Redis.
    Returns None if the job is not found.
    """
    import redis.asyncio as aioredis

    from app.config import settings

    r = aioredis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=0.1,
        socket_timeout=0.1,
    )
    try:
        meta_key = f"cv_job:{job_id}:meta"
        meta_raw = await r.get(meta_key)
        if meta_raw is None:
            legacy_key = f"cv_job:{job_id}:status"
            legacy_raw = await r.get(legacy_key)
            if legacy_raw is None:
                return None
            return json.loads(legacy_raw)

        meta = json.loads(meta_raw)
        total = int(meta.get("total", 0))
        progress_keys = [
            key for key in await r.keys(f"cv_job:{job_id}:*")
            if key not in {meta_key, meta_key.encode()}
        ]
        progress_raw = await r.mget(progress_keys) if progress_keys else []

        processed = 0
        failed = 0
        errors: list[dict[str, str]] = []

        for raw in progress_raw:
            if raw is None:
                continue
            item = json.loads(raw)
            item_status = item.get("status")
            if item_status == "complete":
                processed += 1
            elif item_status == "failed":
                failed += 1
                errors.append(
                    {
                        "filename": item.get("filename", ""),
                        "error": item.get("error", "unknown_error"),
                    }
                )

        finished = processed + failed
        if total and finished >= total:
            status = "failed" if failed == total else "complete"
        else:
            status = "processing"

        return {
            "job_id": job_id,
            "total": total,
            "processed": processed,
            "failed": failed,
            "errors": errors,
            "status": status,
        }
    finally:
        await r.aclose()


async def _store_job_meta(job_id: str, total: int) -> None:
    """Store aggregate batch metadata so status can be computed later."""
    import redis.asyncio as aioredis

    from app.config import settings

    r = aioredis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=0.1,
        socket_timeout=0.1,
    )
    try:
        payload = json.dumps({"job_id": job_id, "total": total, "status": "queued"})
        await r.set(f"cv_job:{job_id}:meta", payload, ex=3600)
    except Exception:  # noqa: BLE001
        logger.warning("Unable to persist upload metadata for job %s", job_id, exc_info=True)
    finally:
        await r.aclose()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _get_extension(filename: str) -> str:
    """Return the lowercase file extension including dot."""
    return Path(filename).suffix.lower()


def _is_zip(filename: str, content_type: str) -> bool:
    """Return True if the file is a ZIP archive."""
    ext = _get_extension(filename)
    return ext == ".zip" or content_type in (
        "application/zip",
        "application/x-zip-compressed",
    )


def _validate_single_file(filename: str, size: int) -> str | None:
    """
    Validate a single (non-ZIP) file.

    Returns None if valid, or an error message string if invalid.
    """
    ext = _get_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        return f"File type {ext!r} is not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
    if size > MAX_FILE_SIZE_BYTES:
        return f"File size {size} bytes exceeds maximum of {MAX_FILE_SIZE_BYTES} bytes (10MB)"
    return None


def _save_file(filename: str, content: bytes) -> tuple[Path, str]:
    """Save file bytes to /tmp/uploads/{uuid}_{filename}. Returns (path, file_type)."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4()}_{filename}"
    dest = UPLOAD_DIR / unique_name
    dest.write_bytes(content)
    ext = _get_extension(filename)
    return dest, ext


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_file(file: UploadFile) -> JSONResponse:
    """
    Upload a CV file or ZIP batch for processing.

    - Single file: PDF/DOCX/DOC/JPG/PNG, max 10MB
    - ZIP file: contains up to 200 valid CV files

    Returns:
        {job_id: str, file_count: int, status: "queued"}
    """
    filename = file.filename or "upload"
    content_type = file.content_type or ""
    content = await file.read()
    size = len(content)

    # Determine if ZIP
    if _is_zip(filename, content_type):
        return await _handle_zip_upload(content)

    # Validate content-type for single (non-ZIP) uploads
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Content type {content_type!r} is not allowed.",
        )

    # Single file validation
    error_msg = _validate_single_file(filename, size)
    if error_msg:
        raise HTTPException(status_code=422, detail=error_msg)

    # Save and enqueue
    saved_path, file_type = _save_file(filename, content)
    job_id = await enqueue_cv_job(str(saved_path), file_type)
    await _store_job_meta(job_id, total=1)

    return JSONResponse(
        content={"job_id": job_id, "file_count": 1, "status": "queued"}
    )


async def _handle_zip_upload(content: bytes) -> JSONResponse:
    """Handle ZIP batch upload — validate and enqueue each file."""
    try:
        zip_io = io.BytesIO(content)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid ZIP file")

    try:
        with zipfile.ZipFile(zip_io) as zf:
            entries = [
                info for info in zf.infolist()
                if not info.is_dir() and info.filename
            ]

            # Check batch limit FIRST
            if len(entries) > MAX_ZIP_FILES:
                return JSONResponse(
                    status_code=422,
                    content={"error": "batch_limit_exceeded", "count": len(entries)},
                )

            valid_entries: list[zipfile.ZipInfo] = []
            for entry in entries:
                ext = _get_extension(entry.filename)
                if ext not in ALLOWED_EXTENSIONS:
                    logger.warning("Skipping unsupported file in ZIP batch: %s", entry.filename)
                    continue
                if entry.file_size > MAX_FILE_SIZE_BYTES:
                    logger.warning("Skipping oversized file in ZIP batch: %s", entry.filename)
                    continue
                valid_entries.append(entry)

            if not valid_entries:
                raise HTTPException(
                    status_code=422,
                    detail="ZIP does not contain any supported files within the size limit",
                )

            # Enqueue one job per file; use a shared batch job_id
            batch_job_id = str(uuid.uuid4())
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            await _store_job_meta(batch_job_id, total=len(valid_entries))

            for file_index, entry in enumerate(valid_entries):
                # Streaming decompression with byte budget cap (ZIP bomb protection)
                MAX_DECOMPRESSED = MAX_FILE_SIZE_BYTES
                with zf.open(entry.filename) as f:
                    chunks = []
                    total = 0
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_DECOMPRESSED:
                            raise HTTPException(
                                422,
                                detail={
                                    "error": "file_too_large",
                                    "filename": entry.filename,
                                },
                            )
                        chunks.append(chunk)
                    file_bytes = b"".join(chunks)

                saved_path, file_type = _save_file(Path(entry.filename).name, file_bytes)
                await enqueue_cv_job(
                    str(saved_path),
                    file_type,
                    batch_job_id=batch_job_id,
                    file_index=file_index,
                )
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail="Invalid ZIP file")

    return JSONResponse(
        content={
            "job_id": batch_job_id,
            "file_count": len(valid_entries),
            "status": "queued",
        }
    )


@router.get("/upload/{job_id}/status")
async def get_upload_status(job_id: str) -> JSONResponse:
    """
    Get the processing status of an upload job.

    Returns:
        {job_id, total, processed, failed, errors, status}
    """
    status = await get_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")

    return JSONResponse(content=status)
