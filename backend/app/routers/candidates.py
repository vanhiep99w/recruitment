"""Candidate API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, require_auth_context
from app.database import get_db
from app.models.candidate_profile import CandidateProfile
from app.schemas.candidate import (
    CandidateDetailResponse,
    CandidateListResponse,
    CandidateProfileRead,
    CandidateProfileUpdate,
    CandidateReviewRequest,
    CandidateReviewResponse,
)
from app.services.llm_client import LLMClient, get_llm_client
from app.services.search import (
    CandidateSearchFilters,
    build_candidate_embedding_text,
    find_duplicate_candidate,
    get_candidate_detail_for_org,
    list_candidates_for_org,
    serialize_candidate_detail,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse)
async def list_candidates(
    q: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    min_experience: float | None = Query(default=None, ge=0),
    parse_status: str | None = Query(default=None),
    pool_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    llm_client: LLMClient = Depends(get_llm_client),
) -> CandidateListResponse:
    query_embedding = None
    if q:
        try:
            embedded = await llm_client.embed(q)
        except Exception:
            embedded = None
        if isinstance(embedded, list) and embedded and isinstance(embedded[0], float):
            query_embedding = embedded

    payload = await list_candidates_for_org(
        db,
        org_id=auth.org_id,
        filters=CandidateSearchFilters(
            q=q,
            skill=skill,
            min_experience=min_experience,
            parse_status=parse_status,
            pool_id=pool_id,
            page=page,
            limit=limit,
        ),
        query_embedding=query_embedding,
    )
    return CandidateListResponse.model_validate(payload)


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> CandidateDetailResponse:
    candidate = await get_candidate_detail_for_org(
        db,
        org_id=auth.org_id,
        candidate_id=candidate_id,
    )
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return CandidateDetailResponse.model_validate(serialize_candidate_detail(candidate))


@router.patch("/{candidate_id}/profile", response_model=CandidateProfileRead)
async def update_candidate_profile(
    candidate_id: uuid.UUID,
    payload: CandidateProfileUpdate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    llm_client: LLMClient = Depends(get_llm_client),
) -> CandidateProfileRead:
    candidate = await get_candidate_detail_for_org(db, org_id=auth.org_id, candidate_id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    profile = candidate.profile or CandidateProfile(candidate_id=candidate.id)
    if candidate.profile is None:
        db.add(profile)

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    profile.parse_status = "manually_reviewed"
    profile.parsed_at = datetime.now(timezone.utc)

    embedding_text = build_candidate_embedding_text(
        name=candidate.name,
        skills=profile.skills,
        work_experience=profile.work_experience,
    )
    if embedding_text:
        try:
            embedded = await llm_client.embed(embedding_text)
        except Exception:
            embedded = None
        if isinstance(embedded, list) and embedded and isinstance(embedded[0], float):
            profile.embedding = embedded

    await db.flush()
    await db.refresh(profile)
    return CandidateProfileRead.model_validate(profile)


@router.post("/{candidate_id}/review", response_model=CandidateReviewResponse)
async def review_candidate_profile(
    candidate_id: uuid.UUID,
    payload: CandidateReviewRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    llm_client: LLMClient = Depends(get_llm_client),
) -> CandidateReviewResponse:
    candidate = await get_candidate_detail_for_org(db, org_id=auth.org_id, candidate_id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    for field in ("name", "email", "phone", "location"):
        value = getattr(payload, field)
        if value is not None:
            setattr(candidate, field, value)

    profile_update = CandidateProfileUpdate(
        skills=payload.skills,
        work_experience=payload.work_experience,
        education=payload.education,
        languages=payload.languages,
        certifications=payload.certifications,
    )
    await update_candidate_profile(
        candidate_id=candidate_id,
        payload=profile_update,
        db=db,
        auth=auth,
        llm_client=llm_client,
    )

    duplicate = await find_duplicate_candidate(
        db,
        org_id=auth.org_id,
        name=candidate.name,
        email=candidate.email,
        exclude_candidate_id=candidate.id,
    )
    await db.flush()

    refreshed_candidate = await get_candidate_detail_for_org(
        db,
        org_id=auth.org_id,
        candidate_id=candidate_id,
    )
    if refreshed_candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    return CandidateReviewResponse.model_validate(
        {
            "candidate": serialize_candidate_detail(refreshed_candidate),
            "duplicate": duplicate,
        }
    )
