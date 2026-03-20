"""SQLAlchemy model for talent_pools table."""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TalentPool(Base):
    __tablename__ = "talent_pools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="talent_pools")  # noqa: F821
    members: Mapped[list["TalentPoolMember"]] = relationship(  # noqa: F821
        "TalentPoolMember", back_populates="pool"
    )

    def __repr__(self) -> str:
        return f"<TalentPool id={self.id} name={self.name!r}>"
