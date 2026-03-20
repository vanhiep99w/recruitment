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
