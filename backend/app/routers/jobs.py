"""Job API routes."""
from __future__ import annotations

import io
import uuid

from docx import Document
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, require_auth_context
from app.database import get_db
from app.models.jd_profile import JDProfile
from app.models.job import Job
from app.schemas.job import (
    JobCandidateListResponse,
    JobCreateRequest,
    JobListResponse,
    JobMatchRequest,
    JobMatchResult,
    JobWithProfileRead,
)
from app.services.llm_client import LLMClient, get_llm_client
from app.services.match_engine import (
    build_job_embedding_payload,
    build_jd_profile_payload,
    get_job_for_org,
    list_jobs_for_org,
    list_ranked_candidates_for_job,
    score_candidates_for_job,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _extract_uploaded_text(upload: UploadFile) -> str:
    content = await upload.read()
    filename = (upload.filename or "").lower()
    if filename.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if filename.endswith(".docx"):
        document = Document(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Unsupported JD file format. Use PDF or DOCX.",
    )


async def _parse_job_create_payload(
    request: Request,
    title: str | None,
    jd_text: str | None,
    form_status: str | None,
    jd_file: UploadFile | None,
) -> tuple[JobCreateRequest, str | None]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        payload = JobCreateRequest(
            title=title or "",
            jd_text=jd_text,
            status=form_status or "draft",
        )
        extracted_text = await _extract_uploaded_text(jd_file) if jd_file is not None else None
        return payload, extracted_text

    body = await request.json()
    return JobCreateRequest.model_validate(body), None


@router.post("", response_model=JobWithProfileRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: Request,
    title: str | None = Form(default=None),
    jd_text: str | None = Form(default=None),
    form_status: str | None = Form(default=None, alias="status"),
    jd_file: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    llm_client: LLMClient = Depends(get_llm_client),
) -> JobWithProfileRead:
    payload, extracted_text = await _parse_job_create_payload(
        request,
        title=title,
        jd_text=jd_text,
        form_status=form_status,
        jd_file=jd_file,
    )
    jd_text = extracted_text or payload.jd_text
    if not jd_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either jd_text or jd_file is required",
        )

    job = Job(
        title=payload.title,
        jd_text=jd_text,
        status=payload.status,
        org_id=auth.org_id,
    )
    db.add(job)
    await db.flush()

    parsed_jd = await llm_client.parse_jd(jd_text)
    jd_payload = build_jd_profile_payload(parsed_jd)
    profile = JDProfile(job_id=job.id, **jd_payload)
    embedding_text = build_job_embedding_payload(job, jd_payload)
    try:
        embedded = await llm_client.embed(embedding_text)
    except Exception:
        embedded = None
    if isinstance(embedded, list) and embedded and isinstance(embedded[0], float):
        profile.embedding = embedded
    db.add(profile)

    await db.flush()
    await db.refresh(job)
    job.jd_profile = profile
    return JobWithProfileRead.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> JobListResponse:
    payload = await list_jobs_for_org(db, org_id=auth.org_id, page=page, limit=limit)
    return JobListResponse.model_validate(payload)


@router.get("/{job_id}", response_model=JobWithProfileRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> JobWithProfileRead:
    job = await get_job_for_org(db, org_id=auth.org_id, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobWithProfileRead.model_validate(job)


@router.post("/{job_id}/match", response_model=list[JobMatchResult])
async def trigger_job_match(
    job_id: uuid.UUID,
    payload: JobMatchRequest | None = None,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    llm_client: LLMClient = Depends(get_llm_client),
) -> list[JobMatchResult]:
    try:
        matches = await score_candidates_for_job(
            db,
            org_id=auth.org_id,
            job_id=job_id,
            candidate_ids=payload.candidate_ids if payload else None,
            llm_client=llm_client,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [
        JobMatchResult(
            match_id=match.id,
            candidate_id=match.candidate_id,
            overall_score=match.overall_score or 0,
            skill_score=match.skill_score or 0,
            experience_score=match.experience_score or 0,
            education_score=match.education_score or 0,
            rationale=match.rationale or "",
        )
        for match in matches
    ]


@router.get("/{job_id}/candidates", response_model=JobCandidateListResponse)
async def get_ranked_job_candidates(
    job_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> JobCandidateListResponse:
    payload = await list_ranked_candidates_for_job(
        db,
        org_id=auth.org_id,
        job_id=job_id,
        page=page,
        limit=limit,
    )
    return JobCandidateListResponse.model_validate(payload)
