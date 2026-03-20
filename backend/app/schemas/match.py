"""Pydantic schemas for Match and Pipeline."""
import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema


class MatchRead(BaseSchema):
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    overall_score: int | None
    skill_score: int | None
    experience_score: int | None
    education_score: int | None
    rationale: str | None
    created_at: datetime


class PipelineRead(BaseSchema):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    stage: str
    updated_at: datetime


class PipelineUpdate(BaseSchema):
    stage: str = Field(
        ...,
        pattern="^(sourced|screened|shortlisted|interviewed|offered|hired|rejected)$",
    )
