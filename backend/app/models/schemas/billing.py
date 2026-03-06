"""Pydantic schemas for billing and credit operations."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CreditPackInfo(BaseModel):
    """Information about a credit pack."""

    id: str = Field(..., description="Pack identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Pack description")
    credits: int = Field(..., description="Number of credits in pack")
    price_cents: int = Field(..., description="Price in cents")
    price_dollars: float = Field(..., description="Price in dollars")
    price_per_credit: float = Field(..., description="Price per credit in dollars")


class CreditPackListResponse(BaseModel):
    """Response containing list of available credit packs."""

    packs: list[CreditPackInfo]


class CheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session."""

    pack_id: str = Field(
        ...,
        description="Credit pack identifier (e.g., 'pack_10', 'pack_30')",
        examples=["pack_10", "pack_30", "pack_100", "pack_500"],
    )
    success_url: Optional[str] = Field(
        None,
        description="URL to redirect on successful payment. Defaults to frontend billing page.",
    )
    cancel_url: Optional[str] = Field(
        None,
        description="URL to redirect on cancelled payment. Defaults to frontend billing page.",
    )


class CheckoutResponse(BaseModel):
    """Response containing Stripe checkout session details."""

    checkout_url: str = Field(..., description="Stripe checkout page URL")
    session_id: str = Field(..., description="Stripe checkout session ID")


class CustomerPortalResponse(BaseModel):
    """Response containing Stripe customer portal URL."""

    portal_url: str = Field(..., description="Stripe customer portal URL")


class TransactionTypeEnum(str, Enum):
    """Types of credit transactions."""

    PURCHASE = "purchase"
    USAGE = "usage"
    REFUND = "refund"
    BONUS = "bonus"
    SIGNUP = "signup"


class TransactionInfo(BaseModel):
    """Information about a single transaction."""

    id: int = Field(..., description="Transaction ID")
    type: TransactionTypeEnum = Field(..., description="Transaction type")
    amount: int = Field(..., description="Credit amount (negative for usage)")
    description: Optional[str] = Field(None, description="Transaction description")
    stripe_payment_intent_id: Optional[str] = Field(
        None, description="Stripe payment intent ID"
    )
    created_at: datetime = Field(..., description="Transaction timestamp")

    class Config:
        from_attributes = True


class TransactionHistoryResponse(BaseModel):
    """Response containing transaction history."""

    transactions: list[TransactionInfo]
    total: int = Field(..., description="Total number of transactions")
    limit: int = Field(..., description="Number of transactions per page")
    offset: int = Field(..., description="Current offset")


class CreditBalanceResponse(BaseModel):
    """Response containing user's credit balance."""

    balance: int = Field(..., description="Current credit balance")
    lifetime_purchased: int = Field(
        ..., description="Total credits purchased lifetime"
    )


class WebhookEventType(str, Enum):
    """Stripe webhook event types we handle."""

    CHECKOUT_SESSION_COMPLETED = "checkout.session.completed"
    PAYMENT_INTENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_INTENT_FAILED = "payment_intent.payment_failed"


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
