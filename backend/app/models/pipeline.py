"""SQLAlchemy model for pipelines table."""
import uuid
from datetime import datetime

from sqlalchemy import FetchedValue, ForeignKey, String, UniqueConstraint, func
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pipeline(Base):
    __tablename__ = "pipelines"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_pipelines_job_candidate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="sourced",
        comment="sourced|screened|shortlisted|interviewed|offered|hired|rejected"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), server_onupdate=FetchedValue(), nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="pipelines")  # noqa: F821
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="pipelines")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Pipeline id={self.id} job_id={self.job_id} stage={self.stage!r}>"
