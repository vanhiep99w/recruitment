"""SQLAlchemy model for talent_pool_members join table."""
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TalentPoolMember(Base):
    __tablename__ = "talent_pool_members"

    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("talent_pools.id", ondelete="CASCADE"),
        primary_key=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    pool: Mapped["TalentPool"] = relationship("TalentPool", back_populates="members")  # noqa: F821
    candidate: Mapped["Candidate"] = relationship("Candidate")  # noqa: F821

    def __repr__(self) -> str:
        return f"<TalentPoolMember pool_id={self.pool_id} candidate_id={self.candidate_id}>"
