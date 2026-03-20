"""Pydantic schemas for Organization."""
import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema


class OrganizationCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    plan_tier: str = Field(default="free", pattern="^(free|starter|pro|enterprise)$")
    seats: int = Field(default=5, ge=1)


class OrganizationRead(BaseSchema):
    id: uuid.UUID
    name: str
    plan_tier: str
    seats: int
    created_at: datetime


class OrganizationUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan_tier: str | None = None
    seats: int | None = Field(default=None, ge=1)
