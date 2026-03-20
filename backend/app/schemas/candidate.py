"""Pydantic schemas for Candidate and CandidateProfile."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class CandidateCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    org_id: uuid.UUID


class CandidateRead(BaseSchema):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    location: str | None
    org_id: uuid.UUID
    created_at: datetime


class CandidateUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None


class CandidateProfileRead(BaseSchema):
    id: uuid.UUID
    candidate_id: uuid.UUID
    skills: list[str] | None
    work_experience: Any | None
    education: Any | None
    languages: list[str] | None
    certifications: list[str] | None
    parse_status: str | None
    parsed_at: datetime | None


class CandidateProfileUpdate(BaseSchema):
    skills: list[str] | None = None
    work_experience: Any | None = None
    education: Any | None = None
    languages: list[str] | None = None
    certifications: list[str] | None = None


class CandidateListItem(BaseSchema):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    location: str | None
    parse_status: str | None
    skills: list[str] = Field(default_factory=list)
    created_at: datetime


class CandidateListResponse(BaseSchema):
    data: list[CandidateListItem]
    total: int
    page: int
    limit: int


class CVRead(BaseSchema):
    id: uuid.UUID
    file_url: str
    file_type: str
    upload_ts: datetime
    parse_status: str | None
    raw_text: str | None


class MatchHistoryRead(BaseSchema):
    id: uuid.UUID
    job_id: uuid.UUID
    overall_score: int | None
    skill_score: int | None
    experience_score: int | None
    education_score: int | None
    rationale: str | None
    created_at: datetime


class CandidateDetailResponse(BaseSchema):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    location: str | None
    org_id: uuid.UUID
    created_at: datetime
    profile: CandidateProfileRead | None
    cvs: list[CVRead] = Field(default_factory=list)
    matches: list[MatchHistoryRead] = Field(default_factory=list)


class CandidateReviewRequest(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    skills: list[str] | None = None
    work_experience: Any | None = None
    education: Any | None = None
    languages: list[str] | None = None
    certifications: list[str] | None = None


class DuplicateCandidateHint(BaseSchema):
    duplicate: bool = True
    existing_id: uuid.UUID
    existing_name: str


class CandidateReviewResponse(BaseSchema):
    candidate: CandidateDetailResponse
    duplicate: DuplicateCandidateHint | None = None
