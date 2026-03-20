"""SQLAlchemy model for candidate_profiles table (includes pgvector embedding)."""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = (
        UniqueConstraint("candidate_id", name="uq_candidate_profiles_candidate_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    work_experience: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    education: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    languages: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    certifications: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    # pgvector column — 1536 dimensions (text-embedding-ada-002 / 3-small compatible)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    parse_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="parsed|low_confidence|ocr_low_quality|manually_reviewed|parse_failed"
    )
    parsed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="profile")  # noqa: F821

    def __repr__(self) -> str:
        return f"<CandidateProfile id={self.id} candidate_id={self.candidate_id}>"
