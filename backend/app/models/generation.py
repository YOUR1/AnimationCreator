"""Generation model for tracking animation generation jobs."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class GenerationStatus(str, Enum):
    """Status of a generation job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Generation(Base):
    """Generation model for tracking credit-consuming generation jobs."""

    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Generation details
    generation_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "character" or "animation"
    credits_used: Mapped[int] = mapped_column(Integer, nullable=False)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50),
        default=GenerationStatus.QUEUED.value,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # External job reference (e.g., fal.ai job ID)
    external_job_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="generations")

    def __repr__(self) -> str:
        return f"<Generation(id={self.id}, type={self.generation_type}, status={self.status})>"

    def mark_started(self) -> None:
        """Mark generation as started."""
        self.status = GenerationStatus.PROCESSING.value
        self.started_at = datetime.now()

    def mark_completed(self) -> None:
        """Mark generation as completed."""
        self.status = GenerationStatus.COMPLETED.value
        self.completed_at = datetime.now()

    def mark_failed(self, error_message: str) -> None:
        """Mark generation as failed with error message."""
        self.status = GenerationStatus.FAILED.value
        self.error_message = error_message
        self.completed_at = datetime.now()
