"""Animation model for character animations."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.character import Character


class AnimationStatus(str, Enum):
    """Status of an animation generation."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Animation(Base):
    """Animation model representing generated character animations."""

    __tablename__ = "animations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Animation type/state (idle, dancing, sad, excited, etc.)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Generated outputs
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gif_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50),
        default=AnimationStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Generation reference
    generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("generations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    character: Mapped["Character"] = relationship(
        "Character", back_populates="animations"
    )

    def __repr__(self) -> str:
        return f"<Animation(id={self.id}, state={self.state}, status={self.status})>"
