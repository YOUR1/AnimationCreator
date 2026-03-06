"""User model for authentication and profile management."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.credit import Credit
    from app.models.generation import Generation
    from app.models.transaction import Transaction


class User(Base):
    """User model representing authenticated users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # OAuth provider info
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Stripe integration
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, unique=True
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)

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
    credits: Mapped["Credit"] = relationship(
        "Credit",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        lazy="selectin",
    )
    characters: Mapped[list["Character"]] = relationship(
        "Character",
        back_populates="user",
        lazy="selectin",
    )
    generations: Mapped[list["Generation"]] = relationship(
        "Generation",
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
