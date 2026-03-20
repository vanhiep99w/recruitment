"""Pydantic schemas for TalentPool and TalentPoolMember."""
import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema


class TalentPoolCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    org_id: uuid.UUID


class TalentPoolCreateRequest(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)


class TalentPoolRead(BaseSchema):
    id: uuid.UUID
    name: str
    org_id: uuid.UUID
    created_at: datetime


class TalentPoolUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class TalentPoolMemberAdd(BaseSchema):
    candidate_id: uuid.UUID


class TalentPoolMemberBatchAdd(BaseSchema):
    candidate_ids: list[uuid.UUID] = Field(min_length=1)


class TalentPoolListItem(BaseSchema):
    id: uuid.UUID
    name: str
    org_id: uuid.UUID
    created_at: datetime
    candidate_count: int = 0


class TalentPoolListResponse(BaseSchema):
    data: list[TalentPoolListItem]
