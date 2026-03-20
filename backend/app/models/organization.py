"""SQLAlchemy model for organizations table."""
import uuid
from datetime import datetime

from sqlalchemy import Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organization")  # noqa: F821
    candidates: Mapped[list["Candidate"]] = relationship("Candidate", back_populates="organization")  # noqa: F821
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="organization")  # noqa: F821
    talent_pools: Mapped[list["TalentPool"]] = relationship("TalentPool", back_populates="organization")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name!r}>"
