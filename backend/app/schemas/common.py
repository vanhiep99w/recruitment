"""Common Pydantic schema utilities and base classes."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common config."""
    model_config = ConfigDict(from_attributes=True)


class UUIDMixin(BaseSchema):
    """Mixin for models that have a UUID primary key."""
    id: uuid.UUID


class TimestampMixin(BaseSchema):
    """Mixin for models with created_at timestamp."""
    created_at: datetime
