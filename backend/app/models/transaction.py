"""Transaction model for tracking credit purchases and usage."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class TransactionType(str, Enum):
    """Types of credit transactions."""

    PURCHASE = "purchase"  # User bought credits via Stripe
    USAGE = "usage"  # Credits used for generation
    REFUND = "refund"  # Credits refunded
    BONUS = "bonus"  # Promotional/bonus credits
    SIGNUP = "signup"  # Initial signup credits


class Transaction(Base):
    """Transaction model for credit movements."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transaction details
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Stripe integration
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    stripe_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Reference to related generation (for usage transactions)
    generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("generations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type={self.type}, amount={self.amount})>"
