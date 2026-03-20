"""SQLAlchemy model for jobs table."""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft",
        comment="draft|active|closed|archived"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="jobs")  # noqa: F821
    jd_profile: Mapped["JDProfile | None"] = relationship(  # noqa: F821
        "JDProfile", back_populates="job", uselist=False
    )
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="job")  # noqa: F821
    pipelines: Mapped[list["Pipeline"]] = relationship("Pipeline", back_populates="job")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title!r} status={self.status!r}>"
