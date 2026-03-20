"""
Tests for Upload Router — POST /api/upload and GET /api/upload/{job_id}/status.
Phase 1: RED — tests written before implementation.
"""
import io
import json
import zipfile
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_bytes(size_bytes: int = 1024) -> bytes:
    """Return a minimal fake PDF byte string of approximately given size."""
    header = b"%PDF-1.4\n"
    padding = b"%" + b"x" * (size_bytes - len(header))
    return header + padding


def _make_zip_bytes(file_count: int, file_size: int = 512) -> bytes:
    """Return a ZIP archive containing `file_count` fake PDF files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(file_count):
            zf.writestr(f"cv_{i:04d}.pdf", _make_pdf_bytes(file_size))
    buf.seek(0)
    return buf.read()


def _get_client():
    from app.main import app
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# POST /api/upload — single file
# ---------------------------------------------------------------------------

class TestUploadSingleFile:
    """Tests for single-file uploads."""

    @pytest.mark.anyio
    async def test_upload_valid_pdf_returns_queued(self):
        """POST /api/upload with valid PDF → {job_id, file_count: 1, status: 'queued'}."""
        with (
            patch("app.routers.upload.enqueue_cv_job", new_callable=AsyncMock) as mock_enqueue,
            patch("app.routers.upload._store_job_meta", new_callable=AsyncMock),
        ):
            mock_enqueue.return_value = "test-job-id-001"
            async with _get_client() as client:
                pdf_bytes = _make_pdf_bytes(2048)
                response = await client.post(
                    "/api/upload",
                    files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
                )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "job_id" in data
        assert data["file_count"] == 1
        assert data["status"] == "queued"

    @pytest.mark.anyio
    async def test_upload_valid_docx_returns_queued(self):
        """POST /api/upload with valid DOCX file → queued."""
        with (
            patch("app.routers.upload.enqueue_cv_job", new_callable=AsyncMock) as mock_enqueue,
            patch("app.routers.upload._store_job_meta", new_callable=AsyncMock),
        ):
            mock_enqueue.return_value = "test-job-id-002"
            async with _get_client() as client:
                docx_bytes = b"PK\x03\x04" + b"\x00" * 100  # fake DOCX header
                response = await client.post(
                    "/api/upload",
                    files={
                        "file": (
                            "resume.docx",
                            io.BytesIO(docx_bytes),
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    },
                )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["file_count"] == 1
        assert data["status"] == "queued"

    @pytest.mark.anyio
    async def test_upload_valid_jpg_returns_queued(self):
        """POST /api/upload with valid JPG file → queued."""
        with (
            patch("app.routers.upload.enqueue_cv_job", new_callable=AsyncMock) as mock_enqueue,
            patch("app.routers.upload._store_job_meta", new_callable=AsyncMock),
        ):
            mock_enqueue.return_value = "test-job-id-003"
            async with _get_client() as client:
                jpg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG magic bytes
                response = await client.post(
                    "/api/upload",
                    files={"file": ("photo.jpg", io.BytesIO(jpg_bytes), "image/jpeg")},
                )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["file_count"] == 1
        assert data["status"] == "queued"

    @pytest.mark.anyio
    async def test_upload_invalid_file_type_returns_422(self):
        """POST /api/upload with unsupported file type → 422."""
        async with _get_client() as client:
            response = await client.post(
                "/api/upload",
                files={"file": ("malware.exe", io.BytesIO(b"MZ\x00" * 50), "application/octet-stream")},
            )
        assert response.status_code == 422, response.text

    @pytest.mark.anyio
    async def test_upload_txt_file_returns_422(self):
        """POST /api/upload with .txt file → 422."""
        async with _get_client() as client:
            response = await client.post(
                "/api/upload",
                files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
            )
        assert response.status_code == 422, response.text

    @pytest.mark.anyio
    async def test_upload_file_too_large_returns_422(self):
        """POST /api/upload with file > 10MB → 422."""
        with patch("app.routers.upload.MAX_FILE_SIZE_BYTES", 1024):
            async with _get_client() as client:
                large_bytes = b"%PDF-1.4\n" + b"x" * 2048
                response = await client.post(
                    "/api/upload",
                    files={"file": ("huge.pdf", io.BytesIO(large_bytes), "application/pdf")},
                )
        assert response.status_code == 422, response.text

    @pytest.mark.anyio
    async def test_upload_response_has_job_id(self):
        """Response from valid upload must contain a non-empty job_id string."""
        with (
            patch("app.routers.upload.enqueue_cv_job", new_callable=AsyncMock) as mock_enqueue,
            patch("app.routers.upload._store_job_meta", new_callable=AsyncMock),
        ):
            mock_enqueue.return_value = "uuid-abc-123"
            async with _get_client() as client:
                pdf_bytes = _make_pdf_bytes(2048)
                response = await client.post(
                    "/api/upload",
                    files={"file": ("cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
                )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["job_id"], str)
        assert len(data["job_id"]) > 0


# ---------------------------------------------------------------------------
# POST /api/upload — ZIP batch
# ---------------------------------------------------------------------------

class TestUploadZipBatch:
    """Tests for ZIP batch uploads."""

    @pytest.mark.anyio
    async def test_upload_zip_with_5_files_returns_queued(self):
        """POST /api/upload with ZIP of 5 files → {job_id, file_count: 5, status: 'queued'}."""
        with (
            patch("app.routers.upload.enqueue_cv_job", new_callable=AsyncMock) as mock_enqueue,
            patch("app.routers.upload._store_job_meta", new_callable=AsyncMock),
        ):
            mock_enqueue.return_value = "batch-job-001"
            async with _get_client() as client:
                zip_bytes = _make_zip_bytes(5)
                response = await client.post(
                    "/api/upload",
                    files={"file": ("batch.zip", io.BytesIO(zip_bytes), "application/zip")},
                )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["file_count"] == 5
        assert data["status"] == "queued"

    @pytest.mark.anyio
    async def test_upload_zip_exactly_200_files_returns_queued(self):
        """POST /api/upload with ZIP of exactly 200 files → 200 OK."""
        with (
            patch("app.routers.upload.enqueue_cv_job", new_callable=AsyncMock) as mock_enqueue,
            patch("app.routers.upload._store_job_meta", new_callable=AsyncMock),
        ):
            mock_enqueue.return_value = "batch-job-200"
            async with _get_client() as client:
                zip_bytes = _make_zip_bytes(200)
                response = await client.post(
                    "/api/upload",
                    files={"file": ("batch200.zip", io.BytesIO(zip_bytes), "application/zip")},
                )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["file_count"] == 200

    @pytest.mark.anyio
    async def test_upload_zip_201_files_returns_422_batch_limit_exceeded(self):
        """POST /api/upload with ZIP of 201 files → 422 with error='batch_limit_exceeded'."""
        async with _get_client() as client:
            zip_bytes = _make_zip_bytes(201)
            response = await client.post(
                "/api/upload",
                files={"file": ("too_big.zip", io.BytesIO(zip_bytes), "application/zip")},
            )
        assert response.status_code == 422, response.text
        data = response.json()
        assert data.get("error") == "batch_limit_exceeded"
        assert "count" in data
        assert data["count"] == 201

    @pytest.mark.anyio
    async def test_upload_zip_with_invalid_file_inside_queues_valid_files_only(self):
        """ZIP with one bad file still queues the valid files."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("resume.pdf", _make_pdf_bytes(512))
            zf.writestr("malware.exe", b"MZ" * 50)  # invalid
        buf.seek(0)
        with (
            patch("app.routers.upload.enqueue_cv_job", new_callable=AsyncMock) as mock_enqueue,
            patch("app.routers.upload._store_job_meta", new_callable=AsyncMock),
        ):
            async with _get_client() as client:
                response = await client.post(
                    "/api/upload",
                    files={"file": ("mixed.zip", buf, "application/zip")},
                )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["file_count"] == 1
        assert data["status"] == "queued"
        assert mock_enqueue.await_count == 1

    @pytest.mark.anyio
    async def test_upload_zip_job_id_is_string(self):
        """ZIP upload response must contain string job_id."""
        with (
            patch("app.routers.upload.enqueue_cv_job", new_callable=AsyncMock) as mock_enqueue,
            patch("app.routers.upload._store_job_meta", new_callable=AsyncMock),
        ):
            mock_enqueue.return_value = "batch-uuid-xyz"
            async with _get_client() as client:
                zip_bytes = _make_zip_bytes(3)
                response = await client.post(
                    "/api/upload",
                    files={"file": ("cvs.zip", io.BytesIO(zip_bytes), "application/zip")},
                )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["job_id"], str)


# ---------------------------------------------------------------------------
# GET /api/upload/{job_id}/status
# ---------------------------------------------------------------------------

class TestUploadStatus:
    """Tests for job status endpoint."""

    @pytest.mark.anyio
    async def test_get_status_returns_status_object(self):
        """GET /api/upload/{job_id}/status → returns status object."""
        with patch("app.routers.upload.get_job_status", new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {
                "job_id": "abc-123",
                "total": 5,
                "processed": 3,
                "failed": 1,
                "errors": [{"filename": "bad.pdf", "error": "parse error"}],
                "status": "processing",
            }
            async with _get_client() as client:
                response = await client.get("/api/upload/abc-123/status")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["job_id"] == "abc-123"
        assert data["total"] == 5
        assert data["processed"] == 3
        assert data["failed"] == 1
        assert isinstance(data["errors"], list)
        assert data["status"] == "processing"

    @pytest.mark.anyio
    async def test_get_status_complete(self):
        """GET /api/upload/{job_id}/status → status='complete' when done."""
        with patch("app.routers.upload.get_job_status", new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {
                "job_id": "done-456",
                "total": 10,
                "processed": 10,
                "failed": 0,
                "errors": [],
                "status": "complete",
            }
            async with _get_client() as client:
                response = await client.get("/api/upload/done-456/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["processed"] == 10
        assert data["failed"] == 0

    @pytest.mark.anyio
    async def test_get_status_not_found_returns_404(self):
        """GET /api/upload/{job_id}/status for unknown job → 404."""
        with patch("app.routers.upload.get_job_status", new_callable=AsyncMock) as mock_status:
            mock_status.return_value = None
            async with _get_client() as client:
                response = await client.get("/api/upload/nonexistent-job/status")
        assert response.status_code == 404, response.text

    @pytest.mark.anyio
    async def test_get_status_has_required_fields(self):
        """Status response must have all required fields."""
        with patch("app.routers.upload.get_job_status", new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {
                "job_id": "xyz-789",
                "total": 1,
                "processed": 0,
                "failed": 0,
                "errors": [],
                "status": "processing",
            }
            async with _get_client() as client:
                response = await client.get("/api/upload/xyz-789/status")
        data = response.json()
        required_fields = {"job_id", "total", "processed", "failed", "errors", "status"}
        assert required_fields.issubset(data.keys())

    @pytest.mark.anyio
    async def test_get_job_status_aggregates_redis_progress(self):
        """get_job_status() aggregates per-file Redis results into API status shape."""
        from app.routers.upload import get_job_status

        class FakeRedis:
            async def get(self, key):
                if key == "cv_job:batch-123:meta":
                    return json.dumps({"job_id": "batch-123", "total": 3}).encode()
                return None

            async def keys(self, pattern):
                assert pattern == "cv_job:batch-123:*"
                return [
                    b"cv_job:batch-123:0",
                    b"cv_job:batch-123:1",
                    b"cv_job:batch-123:2",
                    b"cv_job:batch-123:meta",
                ]

            async def mget(self, keys):
                mapping = {
                    b"cv_job:batch-123:0": json.dumps(
                        {"filename": "a.pdf", "status": "complete", "error": None}
                    ).encode(),
                    b"cv_job:batch-123:1": json.dumps(
                        {"filename": "b.pdf", "status": "failed", "error": "parse error"}
                    ).encode(),
                    b"cv_job:batch-123:2": json.dumps(
                        {"filename": "c.pdf", "status": "queued", "error": None}
                    ).encode(),
                    b"cv_job:batch-123:meta": json.dumps(
                        {"job_id": "batch-123", "total": 3}
                    ).encode(),
                }
                return [mapping[key] for key in keys]

            async def aclose(self):
                return None

        fake_redis = FakeRedis()
        with patch("redis.asyncio.from_url", return_value=fake_redis):
            status = await get_job_status("batch-123")

        assert status == {
            "job_id": "batch-123",
            "total": 3,
            "processed": 1,
            "failed": 1,
            "errors": [{"filename": "b.pdf", "error": "parse error"}],
            "status": "processing",
        }
