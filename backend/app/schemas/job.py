"""Pydantic schemas for Job and JDProfile."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema


class JobCreate(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    org_id: uuid.UUID
    jd_text: str | None = None
    status: str = Field(default="draft", pattern="^(draft|active|closed|archived)$")


class JobRead(BaseSchema):
    id: uuid.UUID
    title: str
    org_id: uuid.UUID
    jd_text: str | None
    status: str
    created_at: datetime


class JobUpdate(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    jd_text: str | None = None
    status: str | None = Field(None, pattern=r"^(draft|active|closed|archived)$")


class JDProfileRead(BaseSchema):
    id: uuid.UUID
    job_id: uuid.UUID
    required_skills: list[str] | None
    nice_to_have_skills: list[str] | None
    seniority: str | None
    experience_years_min: int | None
    experience_years_max: int | None
    responsibilities: Any | None


class JobCreateRequest(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    jd_text: str | None = None
    status: str = Field(default="draft", pattern="^(draft|active|closed|archived)$")


class JobWithProfileRead(BaseSchema):
    id: uuid.UUID
    title: str
    org_id: uuid.UUID
    jd_text: str | None
    status: str
    created_at: datetime
    jd_profile: JDProfileRead | None = None


class JobListItem(BaseSchema):
    id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    candidate_count: int = 0


class JobListResponse(BaseSchema):
    data: list[JobListItem]
    total: int
    page: int
    limit: int


class JobMatchRequest(BaseSchema):
    candidate_ids: list[uuid.UUID] | None = None


class JobMatchResult(BaseSchema):
    match_id: uuid.UUID
    candidate_id: uuid.UUID
    overall_score: int
    skill_score: int
    experience_score: int
    education_score: int
    rationale: str


class JobCandidateListItem(BaseSchema):
    candidate_id: uuid.UUID
    name: str
    email: str | None
    location: str | None
    pipeline_stage: str | None
    overall_score: int | None
    skill_score: int | None
    experience_score: int | None
    education_score: int | None
    rationale: str | None


class JobCandidateListResponse(BaseSchema):
    data: list[JobCandidateListItem]
    total: int
    page: int
    limit: int
