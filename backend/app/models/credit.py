"""Credit model for managing user credit balances."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Credit(Base):
    """Credit model for tracking user credit balances."""

    __tablename__ = "credits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Credit balance
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_purchased: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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
    user: Mapped["User"] = relationship("User", back_populates="credits")

    def __repr__(self) -> str:
        return f"<Credit(user_id={self.user_id}, balance={self.balance})>"

    def has_sufficient_credits(self, amount: int) -> bool:
        """Check if user has enough credits."""
        return self.balance >= amount

    def deduct(self, amount: int) -> bool:
        """Deduct credits if sufficient balance exists."""
        if not self.has_sufficient_credits(amount):
            return False
        self.balance -= amount
        return True

    def add(self, amount: int, is_purchase: bool = False) -> None:
        """Add credits to balance."""
        self.balance += amount
        if is_purchase:
            self.lifetime_purchased += amount
