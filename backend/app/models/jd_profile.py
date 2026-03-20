"""SQLAlchemy model for jd_profiles table (includes pgvector embedding)."""
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JDProfile(Base):
    __tablename__ = "jd_profiles"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_jd_profiles_job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    required_skills: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    nice_to_have_skills: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    seniority: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="junior|mid|senior|lead|unspecified"
    )
    experience_years_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_years_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    responsibilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # pgvector column — 1536 dimensions
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="jd_profile")  # noqa: F821

    def __repr__(self) -> str:
        return f"<JDProfile id={self.id} job_id={self.job_id}>"
