"""Pydantic schemas for User."""
import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class UserCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    role: str = Field(default="recruiter", pattern="^(admin|recruiter|viewer)$")
    org_id: uuid.UUID


class UserRead(BaseSchema):
    id: uuid.UUID
    name: str
    email: str
    role: str
    org_id: uuid.UUID
    created_at: datetime


class UserUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(None, pattern=r"^(admin|recruiter|viewer)$")


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
