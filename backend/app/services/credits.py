"""Credit management service for handling user credit operations.

This module provides atomic credit operations with proper transaction handling
to prevent race conditions and ensure data consistency.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import CREDIT_COSTS, get_settings
from app.models.credit import Credit
from app.models.transaction import Transaction, TransactionType
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits for an operation."""

    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient credits: required {required}, available {available}"
        )


class UserNotFoundError(Exception):
    """Raised when user is not found in the database."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


class CreditService:
    """Service for managing user credits with atomic transactions."""

    def __init__(self, db: AsyncSession):
        """Initialize credit service with database session.

        Args:
            db: Async SQLAlchemy session.
        """
        self.db = db

    async def _get_user_with_credits(
        self, user_id: int, for_update: bool = False
    ) -> User:
        """Get user with credits relationship, optionally locking for update.

        Args:
            user_id: The user ID to fetch.
            for_update: If True, lock the row for update to prevent race conditions.

        Returns:
            User object with credits loaded.

        Raises:
            UserNotFoundError: If user doesn't exist.
        """
        query = (
            select(User)
            .options(selectinload(User.credits))
            .where(User.id == user_id)
        )

        if for_update:
            query = query.with_for_update()

        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundError(user_id)

        return user

    async def _get_or_create_credits(self, user_id: int) -> Credit:
        """Get or create credit record for a user.

        Args:
            user_id: The user ID.

        Returns:
            Credit object for the user.
        """
        # Lock the credit row for update
        query = (
            select(Credit)
            .where(Credit.user_id == user_id)
            .with_for_update()
        )
        result = await self.db.execute(query)
        credit = result.scalar_one_or_none()

        if not credit:
            # Create new credit record
            credit = Credit(
                user_id=user_id,
                balance=settings.default_credits_on_signup,
            )
            self.db.add(credit)
            await self.db.flush()

        return credit

    async def deduct_credits(
        self,
        user_id: int,
        amount: int,
        reason: str,
        generation_id: Optional[int] = None,
    ) -> bool:
        """Deduct credits from user account atomically.

        This operation uses database row locking to prevent race conditions
        when multiple concurrent requests try to deduct credits.

        Args:
            user_id: The user ID to deduct credits from.
            amount: Number of credits to deduct (must be positive).
            reason: Description of the operation (e.g., 'character_generation').
            generation_id: Optional reference to related generation.

        Returns:
            True if deduction was successful.

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits.
            UserNotFoundError: If user doesn't exist.
            ValueError: If amount is not positive.
        """
        if amount <= 0:
            raise ValueError("Deduction amount must be positive")

        # Get credit record with row lock
        credit = await self._get_or_create_credits(user_id)

        if not credit.has_sufficient_credits(amount):
            raise InsufficientCreditsError(
                required=amount,
                available=credit.balance,
            )

        # Perform deduction
        credit.deduct(amount)

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.USAGE.value,
            amount=-amount,  # Negative for deductions
            description=reason,
            generation_id=generation_id,
        )
        self.db.add(transaction)

        await self.db.flush()

        logger.info(
            "Deducted %d credits from user %d for %s. New balance: %d",
            amount,
            user_id,
            reason,
            credit.balance,
        )

        return True

    async def get_credit_balance(self, user_id: int) -> int:
        """Get current credit balance for a user.

        Args:
            user_id: The user ID to check.

        Returns:
            Current credit balance.

        Raises:
            UserNotFoundError: If user doesn't exist.
        """
        query = select(Credit).where(Credit.user_id == user_id)
        result = await self.db.execute(query)
        credit = result.scalar_one_or_none()

        if not credit:
            # User exists but has no credit record yet
            # Return default signup credits
            return settings.default_credits_on_signup

        return credit.balance

    async def add_credits(
        self,
        user_id: int,
        amount: int,
        transaction_id: str,
        transaction_type: TransactionType = TransactionType.PURCHASE,
        description: Optional[str] = None,
        stripe_session_id: Optional[str] = None,
    ) -> None:
        """Add credits to user account atomically.

        This operation uses database row locking to prevent race conditions
        when multiple concurrent requests try to add credits.

        Args:
            user_id: The user ID to add credits to.
            amount: Number of credits to add (must be positive).
            transaction_id: Unique transaction identifier (e.g., Stripe payment intent ID).
            transaction_type: Type of transaction (purchase, bonus, refund, etc.).
            description: Optional description of the transaction.
            stripe_session_id: Optional Stripe checkout session ID.

        Raises:
            ValueError: If amount is not positive.
            UserNotFoundError: If user doesn't exist.
        """
        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        # Verify user exists
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(user_id)

        # Check for duplicate transaction (idempotency)
        existing_txn_query = select(Transaction).where(
            Transaction.stripe_payment_intent_id == transaction_id
        )
        existing_result = await self.db.execute(existing_txn_query)
        if existing_result.scalar_one_or_none():
            logger.warning(
                "Duplicate transaction detected: %s for user %d",
                transaction_id,
                user_id,
            )
            return  # Idempotent - don't add credits again

        # Get or create credit record with lock
        credit = await self._get_or_create_credits(user_id)

        # Add credits
        is_purchase = transaction_type == TransactionType.PURCHASE
        credit.add(amount, is_purchase=is_purchase)

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=transaction_type.value,
            amount=amount,  # Positive for additions
            description=description or f"Added {amount} credits",
            stripe_payment_intent_id=transaction_id,
            stripe_session_id=stripe_session_id,
        )
        self.db.add(transaction)

        await self.db.flush()

        logger.info(
            "Added %d credits to user %d (%s). New balance: %d",
            amount,
            user_id,
            transaction_type.value,
            credit.balance,
        )

    async def refund_credits(
        self,
        user_id: int,
        amount: int,
        reason: str,
        generation_id: Optional[int] = None,
    ) -> None:
        """Refund credits to user account (e.g., when generation fails).

        Args:
            user_id: The user ID to refund credits to.
            amount: Number of credits to refund (must be positive).
            reason: Description of why credits are being refunded.
            generation_id: Optional reference to related generation.

        Raises:
            ValueError: If amount is not positive.
            UserNotFoundError: If user doesn't exist.
        """
        if amount <= 0:
            raise ValueError("Refund amount must be positive")

        # Get or create credit record with lock
        credit = await self._get_or_create_credits(user_id)

        # Add refunded credits
        credit.add(amount, is_purchase=False)

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.REFUND.value,
            amount=amount,  # Positive for refunds
            description=reason,
            generation_id=generation_id,
        )
        self.db.add(transaction)

        await self.db.flush()

        logger.info(
            "Refunded %d credits to user %d: %s. New balance: %d",
            amount,
            user_id,
            reason,
            credit.balance,
        )

    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[TransactionType] = None,
    ) -> list[Transaction]:
        """Get transaction history for a user.

        Args:
            user_id: The user ID to get history for.
            limit: Maximum number of transactions to return.
            offset: Number of transactions to skip.
            transaction_type: Optional filter by transaction type.

        Returns:
            List of Transaction objects.
        """
        query = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if transaction_type:
            query = query.where(Transaction.type == transaction_type.value)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_credit_stats(self, user_id: int) -> dict:
        """Get credit statistics for a user.

        Args:
            user_id: The user ID to get stats for.

        Returns:
            Dictionary with credit statistics.
        """
        credit = await self._get_or_create_credits(user_id)

        return {
            "balance": credit.balance,
            "lifetime_purchased": credit.lifetime_purchased,
            "user_id": user_id,
        }

    async def has_sufficient_credits(self, user_id: int, amount: int) -> bool:
        """Check if user has sufficient credits for an operation.

        Args:
            user_id: The user ID to check.
            amount: Number of credits required.

        Returns:
            True if user has sufficient credits.
        """
        balance = await self.get_credit_balance(user_id)
        return balance >= amount


# Module-level convenience functions for the interface contract


async def deduct_credits(
    db: AsyncSession,
    user_id: int,
    amount: int,
    reason: str,
) -> bool:
    """Deduct credits from user account.

    This is a convenience wrapper for the CreditService.

    Args:
        db: Database session.
        user_id: The user ID (as int, converted from string if needed).
        amount: Number of credits to deduct.
        reason: Description of the operation.

    Returns:
        True if deduction was successful.
    """
    service = CreditService(db)
    return await service.deduct_credits(user_id, amount, reason)


async def get_credit_balance(db: AsyncSession, user_id: int) -> int:
    """Get current credit balance for a user.

    Args:
        db: Database session.
        user_id: The user ID.

    Returns:
        Current credit balance.
    """
    service = CreditService(db)
    return await service.get_credit_balance(user_id)


async def add_credits(
    db: AsyncSession,
    user_id: int,
    amount: int,
    transaction_id: str,
) -> None:
    """Add credits to user account.

    Args:
        db: Database session.
        user_id: The user ID.
        amount: Number of credits to add.
        transaction_id: Unique transaction identifier.
    """
    service = CreditService(db)
    await service.add_credits(user_id, amount, transaction_id)
