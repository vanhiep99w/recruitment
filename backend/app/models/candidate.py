"""SQLAlchemy model for candidates table."""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="candidates")  # noqa: F821
    profile: Mapped["CandidateProfile | None"] = relationship(  # noqa: F821
        "CandidateProfile", back_populates="candidate", uselist=False
    )
    cvs: Mapped[list["CV"]] = relationship("CV", back_populates="candidate")  # noqa: F821
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="candidate")  # noqa: F821
    pipelines: Mapped[list["Pipeline"]] = relationship("Pipeline", back_populates="candidate")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Candidate id={self.id} name={self.name!r}>"
