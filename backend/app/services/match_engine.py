"""Matching and job repository helpers."""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.candidate_profile import CandidateProfile
from app.models.jd_profile import JDProfile
from app.models.job import Job
from app.models.match import Match
from app.models.pipeline import Pipeline
from app.services.search import build_job_embedding_text, years_of_experience


def _normalise_skills(skills: list[str] | None) -> set[str]:
    return {skill.strip().lower() for skill in (skills or []) if skill and skill.strip()}


def calculate_skill_score(
    candidate_skills: list[str] | None,
    required_skills: list[str] | None,
    nice_to_have_skills: list[str] | None,
) -> int:
    candidate_set = _normalise_skills(candidate_skills)
    required_set = _normalise_skills(required_skills)
    nice_set = _normalise_skills(nice_to_have_skills)

    if not required_set and not nice_set:
        return 100 if candidate_set else 0

    required_ratio = (
        len(candidate_set & required_set) / len(required_set)
        if required_set
        else 1.0
    )
    nice_ratio = len(candidate_set & nice_set) / len(nice_set) if nice_set else 1.0
    return round((required_ratio * 0.8 + nice_ratio * 0.2) * 100)


def calculate_experience_score(
    candidate_years: float,
    minimum_years: int | None,
    maximum_years: int | None,
) -> int:
    if minimum_years is None and maximum_years is None:
        return 100 if candidate_years > 0 else 0
    if minimum_years is not None and candidate_years < minimum_years:
        return max(0, round((candidate_years / max(minimum_years, 1)) * 100))
    if maximum_years is not None and candidate_years > maximum_years:
        overshoot = candidate_years - maximum_years
        return max(70, 100 - round(overshoot * 5))
    return 100


def calculate_education_score(education: Any) -> int:
    entries = [str(item).lower() for item in (education or [])]
    if not entries:
        return 60
    joined = " ".join(entries)
    if any(keyword in joined for keyword in ("master", "thạc", "mba", "phd", "doctor")):
        return 100
    if any(keyword in joined for keyword in ("bachelor", "cử nhân", "engineer", "kỹ sư")):
        return 90
    return 75


def calculate_overall_score(skill_score: int, experience_score: int, education_score: int) -> int:
    return round(skill_score * 0.5 + experience_score * 0.3 + education_score * 0.2)


def _fallback_rationale(
    *,
    candidate_name: str,
    skill_score: int,
    experience_score: int,
    education_score: int,
) -> str:
    return (
        f"{candidate_name} shows strongest alignment on skills ({skill_score}/100), "
        f"with experience at {experience_score}/100 and education at {education_score}/100."
    )[:200]


async def _score_single_candidate(
    *,
    candidate: Candidate,
    profile: CandidateProfile | None,
    job: Job,
    jd_profile: JDProfile,
    llm_client: Any | None,
) -> dict[str, Any]:
    skill_score = calculate_skill_score(
        profile.skills if profile else None,
        jd_profile.required_skills,
        jd_profile.nice_to_have_skills,
    )
    experience_score = calculate_experience_score(
        years_of_experience(profile.work_experience if profile else None),
        jd_profile.experience_years_min,
        jd_profile.experience_years_max,
    )
    education_score = calculate_education_score(profile.education if profile else None)
    overall_score = calculate_overall_score(skill_score, experience_score, education_score)

    rationale = _fallback_rationale(
        candidate_name=candidate.name,
        skill_score=skill_score,
        experience_score=experience_score,
        education_score=education_score,
    )
    if llm_client is not None:
        try:
            generated = await llm_client.generate_match_rationale(
                candidate_summary={
                    "name": candidate.name,
                    "skills": profile.skills if profile else [],
                },
                job_summary={
                    "title": job.title,
                    "required_skills": jd_profile.required_skills or [],
                },
                scores={
                    "overall_score": overall_score,
                    "skill_score": skill_score,
                    "experience_score": experience_score,
                    "education_score": education_score,
                },
            )
        except Exception:
            generated = None
        if generated:
            rationale = generated[:200]

    return {
        "candidate_id": candidate.id,
        "overall_score": overall_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "rationale": rationale,
    }


async def score_candidates_for_job(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    job_id: uuid.UUID,
    candidate_ids: list[uuid.UUID] | None = None,
    llm_client: Any | None = None,
) -> list[Match]:
    job = await session.scalar(
        select(Job)
        .options(selectinload(Job.jd_profile))
        .where(Job.id == job_id, Job.org_id == org_id)
    )
    if job is None or job.jd_profile is None:
        raise ValueError("Job not found or JD profile missing")

    candidate_stmt = (
        select(Candidate)
        .options(selectinload(Candidate.profile))
        .where(Candidate.org_id == org_id)
    )
    if candidate_ids:
        candidate_stmt = candidate_stmt.where(Candidate.id.in_(candidate_ids))
    candidates = list((await session.scalars(candidate_stmt)).unique().all())

    scored = await asyncio.gather(
        *[
            _score_single_candidate(
                candidate=candidate,
                profile=candidate.profile,
                job=job,
                jd_profile=job.jd_profile,
                llm_client=llm_client,
            )
            for candidate in candidates
        ]
    )

    persisted_matches: list[Match] = []
    for result in scored:
        existing_match = await session.scalar(
            select(Match).where(
                Match.job_id == job_id,
                Match.candidate_id == result["candidate_id"],
            )
        )
        match = existing_match or Match(
            job_id=job_id,
            candidate_id=result["candidate_id"],
        )
        match.overall_score = result["overall_score"]
        match.skill_score = result["skill_score"]
        match.experience_score = result["experience_score"]
        match.education_score = result["education_score"]
        match.rationale = result["rationale"]
        session.add(match)
        persisted_matches.append(match)

    await session.flush()
    return persisted_matches


async def list_jobs_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    page: int,
    limit: int,
) -> dict[str, Any]:
    jobs = list(
        (
            await session.scalars(
                select(Job)
                .options(selectinload(Job.jd_profile))
                .where(Job.org_id == org_id)
                .order_by(Job.created_at.desc())
            )
        ).all()
    )
    counts = {
        job_id: count
        for job_id, count in (
            await session.execute(
                select(Match.job_id, func.count(Match.candidate_id))
                .join(Job, Job.id == Match.job_id)
                .where(Job.org_id == org_id)
                .group_by(Match.job_id)
            )
        ).all()
    }

    total = len(jobs)
    start = max(page - 1, 0) * limit
    end = start + limit

    return {
        "data": [
            {
                "id": job.id,
                "title": job.title,
                "status": job.status,
                "created_at": job.created_at,
                "candidate_count": counts.get(job.id, 0),
            }
            for job in jobs[start:end]
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


async def get_job_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    job_id: uuid.UUID,
) -> Job | None:
    return await session.scalar(
        select(Job)
        .options(selectinload(Job.jd_profile))
        .where(Job.id == job_id, Job.org_id == org_id)
    )


async def list_ranked_candidates_for_job(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    job_id: uuid.UUID,
    page: int,
    limit: int,
) -> dict[str, Any]:
    rows = (
        await session.execute(
            select(Match, Candidate, Pipeline)
            .join(Candidate, Candidate.id == Match.candidate_id)
            .outerjoin(
                Pipeline,
                (Pipeline.candidate_id == Match.candidate_id) & (Pipeline.job_id == Match.job_id),
            )
            .where(Match.job_id == job_id, Candidate.org_id == org_id)
            .order_by(Match.overall_score.desc().nullslast(), Match.created_at.desc())
        )
    ).all()

    total = len(rows)
    start = max(page - 1, 0) * limit
    end = start + limit

    return {
        "data": [
            {
                "candidate_id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "location": candidate.location,
                "pipeline_stage": pipeline.stage if pipeline else None,
                "overall_score": match.overall_score,
                "skill_score": match.skill_score,
                "experience_score": match.experience_score,
                "education_score": match.education_score,
                "rationale": match.rationale,
            }
            for match, candidate, pipeline in rows[start:end]
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


def build_jd_profile_payload(parsed_jd: dict[str, Any]) -> dict[str, Any]:
    return {
        "required_skills": list(parsed_jd.get("required_skills") or []),
        "nice_to_have_skills": list(parsed_jd.get("nice_to_have_skills") or []),
        "seniority": parsed_jd.get("seniority") or "unspecified",
        "experience_years_min": parsed_jd.get("experience_years_min"),
        "experience_years_max": parsed_jd.get("experience_years_max"),
        "responsibilities": list(parsed_jd.get("responsibilities") or []),
    }


def build_job_embedding_payload(job: Job, jd_payload: dict[str, Any]) -> str:
    return build_job_embedding_text(
        title=job.title,
        required_skills=jd_payload.get("required_skills"),
        responsibilities=jd_payload.get("responsibilities"),
        seniority=jd_payload.get("seniority"),
        experience_years_min=jd_payload.get("experience_years_min"),
        experience_years_max=jd_payload.get("experience_years_max"),
    )
