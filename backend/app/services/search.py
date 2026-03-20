"""Search and candidate repository helpers."""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.candidate_profile import CandidateProfile
from app.models.cv import CV
from app.models.match import Match
from app.models.pipeline import Pipeline
from app.models.talent_pool import TalentPool
from app.models.talent_pool_member import TalentPoolMember


@dataclass(slots=True)
class CandidateSearchFilters:
    q: str | None = None
    skill: str | None = None
    min_experience: float | None = None
    parse_status: str | None = None
    pool_id: uuid.UUID | None = None
    page: int = 1
    limit: int = 20


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def years_of_experience(work_experience: Any) -> float:
    """Estimate total years of experience from structured experience entries."""

    total_days = 0
    for item in _safe_list(work_experience):
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("years"), (int, float)):
            total_days += int(float(item["years"]) * 365)
            continue

        start = _parse_date(item.get("start"))
        end = _parse_date(item.get("end")) or date.today()
        if start and end >= start:
            total_days += (end - start).days

    return round(total_days / 365.25, 1) if total_days else 0.0


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.date()
    return None


def build_candidate_embedding_text(
    *,
    name: str,
    skills: list[str] | None,
    work_experience: Any,
) -> str:
    experience_chunks: list[str] = []
    for item in _safe_list(work_experience):
        if not isinstance(item, dict):
            continue
        experience_chunks.append(
            " ".join(
                str(item.get(key, "")).strip()
                for key in ("title", "company", "description")
                if item.get(key)
            )
        )
    return "\n".join(
        part
        for part in [
            name.strip(),
            ", ".join(skills or []),
            " ".join(chunk for chunk in experience_chunks if chunk),
        ]
        if part
    )


def build_job_embedding_text(
    *,
    title: str,
    required_skills: list[str] | None,
    responsibilities: Any,
    seniority: str | None,
    experience_years_min: int | None,
    experience_years_max: int | None,
) -> str:
    range_text = ""
    if experience_years_min is not None or experience_years_max is not None:
        range_text = (
            f"Experience: {experience_years_min or 0}-{experience_years_max or 'plus'} years"
        )

    responsibility_text = " ".join(str(item) for item in _safe_list(responsibilities))
    return "\n".join(
        part
        for part in [
            title.strip(),
            seniority or "",
            ", ".join(required_skills or []),
            range_text,
            responsibility_text,
        ]
        if part
    )


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return -1.0

    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return -1.0
    return numerator / (left_norm * right_norm)


def candidate_matches_query(candidate: Candidate, query: str) -> bool:
    haystack_parts = [
        candidate.name,
        candidate.email or "",
        candidate.phone or "",
        candidate.location or "",
    ]
    if candidate.profile:
        haystack_parts.extend(candidate.profile.skills or [])
    haystack = " ".join(haystack_parts).lower()
    return query.lower() in haystack


async def list_candidates_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    filters: CandidateSearchFilters,
    query_embedding: list[float] | None = None,
) -> dict[str, Any]:
    stmt = (
        select(Candidate)
        .options(
            selectinload(Candidate.profile),
            selectinload(Candidate.cvs),
            selectinload(Candidate.matches),
        )
        .where(Candidate.org_id == org_id)
        .order_by(Candidate.created_at.desc())
    )

    if filters.pool_id:
        stmt = stmt.join(
            TalentPoolMember,
            TalentPoolMember.candidate_id == Candidate.id,
        ).where(TalentPoolMember.pool_id == filters.pool_id)

    candidates = list((await session.scalars(stmt)).unique().all())

    filtered: list[Candidate] = []
    for candidate in candidates:
        profile = candidate.profile
        if filters.parse_status and (profile is None or profile.parse_status != filters.parse_status):
            continue
        if filters.skill:
            skills = {skill.lower() for skill in (profile.skills or [])} if profile else set()
            if filters.skill.lower() not in skills:
                continue
        if filters.min_experience is not None:
            if years_of_experience(profile.work_experience if profile else None) < filters.min_experience:
                continue
        if filters.q and not candidate_matches_query(candidate, filters.q):
            continue
        filtered.append(candidate)

    if filters.q and query_embedding:
        filtered.sort(
            key=lambda candidate: cosine_similarity(
                candidate.profile.embedding if candidate.profile else None,
                query_embedding,
            ),
            reverse=True,
        )

    total = len(filtered)
    start = max(filters.page - 1, 0) * filters.limit
    end = start + filters.limit
    page_items = filtered[start:end]

    return {
        "data": [
            {
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "location": candidate.location,
                "parse_status": candidate.profile.parse_status if candidate.profile else None,
                "skills": list(candidate.profile.skills or []) if candidate.profile else [],
                "created_at": candidate.created_at,
            }
            for candidate in page_items
        ],
        "total": total,
        "page": filters.page,
        "limit": filters.limit,
    }


async def get_candidate_detail_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> Candidate | None:
    stmt = (
        select(Candidate)
        .options(
            selectinload(Candidate.profile),
            selectinload(Candidate.cvs),
            selectinload(Candidate.matches),
        )
        .where(Candidate.id == candidate_id, Candidate.org_id == org_id)
    )
    return await session.scalar(stmt)


async def find_duplicate_candidate(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    name: str,
    email: str | None,
    exclude_candidate_id: uuid.UUID | None = None,
) -> dict[str, Any] | None:
    base_stmt: Select[tuple[Candidate]] = select(Candidate).where(Candidate.org_id == org_id)
    if exclude_candidate_id:
        base_stmt = base_stmt.where(Candidate.id != exclude_candidate_id)

    if email:
        email_match = await session.scalar(base_stmt.where(func.lower(Candidate.email) == email.lower()))
        if email_match:
            return {
                "duplicate": True,
                "existing_id": email_match.id,
                "existing_name": email_match.name,
            }

    candidates = list((await session.scalars(base_stmt)).all())
    for candidate in candidates:
        similarity = SequenceMatcher(None, candidate.name.lower(), name.lower()).ratio()
        if similarity >= 0.85:
            return {
                "duplicate": True,
                "existing_id": candidate.id,
                "existing_name": candidate.name,
            }

    return None


async def list_talent_pools_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
) -> list[dict[str, Any]]:
    stmt = select(TalentPool).where(TalentPool.org_id == org_id).order_by(TalentPool.created_at.desc())
    pools = list((await session.scalars(stmt)).all())

    counts_stmt = (
        select(
            TalentPoolMember.pool_id,
            func.count(TalentPoolMember.candidate_id),
        )
        .join(TalentPool, TalentPool.id == TalentPoolMember.pool_id)
        .where(TalentPool.org_id == org_id)
        .group_by(TalentPoolMember.pool_id)
    )
    counts = {pool_id: count for pool_id, count in (await session.execute(counts_stmt)).all()}

    return [
        {
            "id": pool.id,
            "name": pool.name,
            "org_id": pool.org_id,
            "created_at": pool.created_at,
            "candidate_count": counts.get(pool.id, 0),
        }
        for pool in pools
    ]


def serialize_candidate_detail(candidate: Candidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "location": candidate.location,
        "org_id": candidate.org_id,
        "created_at": candidate.created_at,
        "profile": (
            {
                "id": candidate.profile.id,
                "candidate_id": candidate.profile.candidate_id,
                "skills": candidate.profile.skills,
                "work_experience": candidate.profile.work_experience,
                "education": candidate.profile.education,
                "languages": candidate.profile.languages,
                "certifications": candidate.profile.certifications,
                "parse_status": candidate.profile.parse_status,
                "parsed_at": candidate.profile.parsed_at,
            }
            if candidate.profile
            else None
        ),
        "cvs": [
            {
                "id": cv.id,
                "file_url": cv.file_url,
                "file_type": cv.file_type,
                "upload_ts": cv.upload_ts,
                "parse_status": cv.parse_status,
                "raw_text": cv.raw_text,
            }
            for cv in sorted(candidate.cvs, key=lambda item: item.upload_ts, reverse=True)
        ],
        "matches": [
            {
                "id": match.id,
                "job_id": match.job_id,
                "overall_score": match.overall_score,
                "skill_score": match.skill_score,
                "experience_score": match.experience_score,
                "education_score": match.education_score,
                "rationale": match.rationale,
                "created_at": match.created_at,
            }
            for match in sorted(candidate.matches, key=lambda item: item.created_at, reverse=True)
        ],
    }
