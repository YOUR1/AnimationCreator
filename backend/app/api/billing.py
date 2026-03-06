"""Billing API routes for credit purchases and Stripe integration.

This module provides endpoints for:
- Creating Stripe checkout sessions for credit purchases
- Handling Stripe webhooks for payment events
- Retrieving billing/transaction history
- Accessing Stripe customer portal
"""

import logging
from typing import Annotated, Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.middleware import AuthenticatedUser
from app.core.stripe_config import (
    CREDIT_PACKS,
    StripeConfig,
    create_checkout_session,
    create_customer_portal_session,
    get_credit_pack,
    list_credit_packs,
    verify_webhook_signature,
)
from app.models.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    CreditBalanceResponse,
    CreditPackInfo,
    CreditPackListResponse,
    CustomerPortalResponse,
    ErrorResponse,
    TransactionHistoryResponse,
    TransactionInfo,
)
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.services.credits import CreditService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/billing", tags=["billing"])


# Type alias for database session dependency
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/packs",
    response_model=CreditPackListResponse,
    summary="List available credit packs",
    description="Get a list of all available credit packs for purchase.",
)
async def list_packs() -> CreditPackListResponse:
    """List all available credit packs."""
    packs = list_credit_packs()

    return CreditPackListResponse(
        packs=[
            CreditPackInfo(
                id=pack.id,
                name=pack.name,
                description=pack.description,
                credits=pack.credits,
                price_cents=pack.price_cents,
                price_dollars=pack.price_dollars,
                price_per_credit=pack.price_per_credit,
            )
            for pack in packs
        ]
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create checkout session",
    description="Create a Stripe checkout session for purchasing credits.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid pack ID"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        500: {"model": ErrorResponse, "description": "Stripe error"},
    },
)
async def create_checkout(
    request: CheckoutRequest,
    user: AuthenticatedUser,
    db: DbSession,
) -> CheckoutResponse:
    """Create a Stripe checkout session for credit purchase."""
    # Validate pack exists
    pack = get_credit_pack(request.pack_id)
    if not pack:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid credit pack: {request.pack_id}",
        )

    # Initialize Stripe
    try:
        stripe_config = StripeConfig.initialize()
    except ValueError as e:
        logger.error("Stripe not configured: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    # Set URLs with defaults
    frontend_url = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    success_url = request.success_url or f"{frontend_url}/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = request.cancel_url or f"{frontend_url}/billing?cancelled=true"

    try:
        session = await create_checkout_session(
            user_id=str(user.id),
            user_email=user.email,
            pack_id=request.pack_id,
            success_url=success_url,
            cancel_url=cancel_url,
            stripe_customer_id=user.stripe_customer_id,
        )

        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
        )

    except ValueError as e:
        logger.error("Checkout error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except stripe.error.StripeError as e:
        logger.error("Stripe error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing error",
        )


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook handler",
    description="Handle Stripe webhook events for payment processing.",
    include_in_schema=False,  # Hide from API docs for security
)
async def handle_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
) -> dict:
    """Handle Stripe webhook events.

    This endpoint receives webhook events from Stripe and processes them
    accordingly. Supported events:
    - checkout.session.completed: Credit purchase completed
    - payment_intent.succeeded: Payment successful
    - payment_intent.payment_failed: Payment failed
    """
    # Get raw body for signature verification
    payload = await request.body()

    # Initialize Stripe config
    try:
        stripe_config = StripeConfig.initialize()
    except ValueError as e:
        logger.error("Stripe not configured: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    webhook_secret = stripe_config.webhook_secret
    if not webhook_secret:
        logger.error("Webhook secret not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    # Verify webhook signature
    try:
        event = verify_webhook_signature(
            payload=payload,
            signature=stripe_signature,
            webhook_secret=webhook_secret,
        )
    except stripe.error.SignatureVerificationError as e:
        logger.warning("Invalid webhook signature: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    logger.info("Received Stripe webhook event: %s", event.type)

    # Handle different event types
    try:
        if event.type == "checkout.session.completed":
            await _handle_checkout_completed(event, db)
        elif event.type == "payment_intent.succeeded":
            await _handle_payment_succeeded(event, db)
        elif event.type == "payment_intent.payment_failed":
            await _handle_payment_failed(event, db)
        else:
            logger.debug("Unhandled webhook event type: %s", event.type)

    except Exception as e:
        logger.exception("Error processing webhook event %s: %s", event.type, e)
        # Return 200 to prevent Stripe retries for handled errors
        # Log error for investigation

    return {"status": "ok"}


async def _handle_checkout_completed(
    event: stripe.Event,
    db: AsyncSession,
) -> None:
    """Handle checkout.session.completed event.

    This is called when a customer completes the checkout flow.
    We add credits to their account and update their Stripe customer ID.
    """
    session = event.data.object

    # Extract metadata
    metadata = session.get("metadata", {})
    user_id_str = metadata.get("user_id")
    pack_id = metadata.get("pack_id")
    credits_str = metadata.get("credits")

    if not all([user_id_str, pack_id, credits_str]):
        logger.error(
            "Missing metadata in checkout session %s: user_id=%s, pack_id=%s, credits=%s",
            session.id,
            user_id_str,
            pack_id,
            credits_str,
        )
        return

    try:
        user_id = int(user_id_str)
        credits_amount = int(credits_str)
    except ValueError:
        logger.error("Invalid metadata values in checkout session %s", session.id)
        return

    # Get payment intent ID for transaction tracking
    payment_intent_id = session.get("payment_intent")
    if not payment_intent_id:
        logger.error("No payment intent in checkout session %s", session.id)
        return

    # Get Stripe customer ID
    stripe_customer_id = session.get("customer")

    # Update user's Stripe customer ID if new
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user and stripe_customer_id and not user.stripe_customer_id:
        user.stripe_customer_id = stripe_customer_id
        logger.info(
            "Updated Stripe customer ID for user %d: %s",
            user_id,
            stripe_customer_id,
        )

    # Add credits to user account
    credit_service = CreditService(db)
    pack = get_credit_pack(pack_id)
    description = f"Purchased {pack.name}" if pack else f"Purchased {credits_amount} credits"

    await credit_service.add_credits(
        user_id=user_id,
        amount=credits_amount,
        transaction_id=payment_intent_id,
        transaction_type=TransactionType.PURCHASE,
        description=description,
        stripe_session_id=session.id,
    )

    await db.commit()

    logger.info(
        "Added %d credits to user %d from checkout session %s",
        credits_amount,
        user_id,
        session.id,
    )


async def _handle_payment_succeeded(
    event: stripe.Event,
    db: AsyncSession,
) -> None:
    """Handle payment_intent.succeeded event.

    This is a backup handler - credits should typically be added via
    checkout.session.completed. This handles cases where we might
    receive this event instead.
    """
    payment_intent = event.data.object

    # Check if we already processed this payment
    existing_txn = await db.execute(
        select(Transaction).where(
            Transaction.stripe_payment_intent_id == payment_intent.id
        )
    )
    if existing_txn.scalar_one_or_none():
        logger.debug(
            "Payment intent %s already processed, skipping",
            payment_intent.id,
        )
        return

    # Extract metadata
    metadata = payment_intent.get("metadata", {})
    user_id_str = metadata.get("user_id")
    pack_id = metadata.get("pack_id")
    credits_str = metadata.get("credits")

    if not all([user_id_str, pack_id, credits_str]):
        logger.debug(
            "Payment intent %s missing metadata, may be from different flow",
            payment_intent.id,
        )
        return

    try:
        user_id = int(user_id_str)
        credits_amount = int(credits_str)
    except ValueError:
        logger.error("Invalid metadata values in payment intent %s", payment_intent.id)
        return

    # Add credits
    credit_service = CreditService(db)
    pack = get_credit_pack(pack_id)
    description = f"Purchased {pack.name}" if pack else f"Purchased {credits_amount} credits"

    await credit_service.add_credits(
        user_id=user_id,
        amount=credits_amount,
        transaction_id=payment_intent.id,
        transaction_type=TransactionType.PURCHASE,
        description=description,
    )

    await db.commit()

    logger.info(
        "Added %d credits to user %d from payment intent %s",
        credits_amount,
        user_id,
        payment_intent.id,
    )


async def _handle_payment_failed(
    event: stripe.Event,
    db: AsyncSession,
) -> None:
    """Handle payment_intent.payment_failed event.

    Log the failure for monitoring. No credits are deducted since
    payment was never successful.
    """
    payment_intent = event.data.object

    metadata = payment_intent.get("metadata", {})
    user_id = metadata.get("user_id")
    pack_id = metadata.get("pack_id")

    error = payment_intent.get("last_payment_error", {})
    error_message = error.get("message", "Unknown error")

    logger.warning(
        "Payment failed for user %s, pack %s: %s (intent: %s)",
        user_id,
        pack_id,
        error_message,
        payment_intent.id,
    )

    # Could trigger notifications here in the future
    # For now, just log the failure


@router.get(
    "/history",
    response_model=TransactionHistoryResponse,
    summary="Get billing history",
    description="Get user's billing and transaction history.",
)
async def get_billing_history(
    user: AuthenticatedUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=100, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    type: Optional[str] = Query(
        default=None,
        description="Filter by transaction type",
        examples=["purchase", "usage", "refund"],
    ),
) -> TransactionHistoryResponse:
    """Get user's billing and transaction history."""
    credit_service = CreditService(db)

    # Convert type string to enum if provided
    transaction_type = None
    if type:
        try:
            transaction_type = TransactionType(type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transaction type: {type}",
            )

    transactions = await credit_service.get_transaction_history(
        user_id=user.id,
        limit=limit,
        offset=offset,
        transaction_type=transaction_type,
    )

    # Get total count
    count_query = select(func.count(Transaction.id)).where(
        Transaction.user_id == user.id
    )
    if transaction_type:
        count_query = count_query.where(Transaction.type == transaction_type.value)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return TransactionHistoryResponse(
        transactions=[
            TransactionInfo(
                id=txn.id,
                type=txn.type,
                amount=txn.amount,
                description=txn.description,
                stripe_payment_intent_id=txn.stripe_payment_intent_id,
                created_at=txn.created_at,
            )
            for txn in transactions
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/portal",
    response_model=CustomerPortalResponse,
    summary="Get customer portal URL",
    description="Get Stripe customer portal URL for managing billing.",
    responses={
        400: {"model": ErrorResponse, "description": "No Stripe customer found"},
        500: {"model": ErrorResponse, "description": "Stripe error"},
    },
)
async def get_customer_portal(
    user: AuthenticatedUser,
    db: DbSession,
    return_url: Optional[str] = Query(
        default=None,
        description="URL to return to after portal session",
    ),
) -> CustomerPortalResponse:
    """Get Stripe customer portal URL."""
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing history found. Please make a purchase first.",
        )

    # Initialize Stripe
    try:
        StripeConfig.initialize()
    except ValueError as e:
        logger.error("Stripe not configured: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    # Set return URL
    frontend_url = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    return_url = return_url or f"{frontend_url}/billing"

    try:
        session = await create_customer_portal_session(
            stripe_customer_id=user.stripe_customer_id,
            return_url=return_url,
        )

        return CustomerPortalResponse(portal_url=session.url)

    except stripe.error.StripeError as e:
        logger.error("Stripe portal error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to access billing portal",
        )


@router.get(
    "/balance",
    response_model=CreditBalanceResponse,
    summary="Get credit balance",
    description="Get user's current credit balance and statistics.",
)
async def get_balance(
    user: AuthenticatedUser,
    db: DbSession,
) -> CreditBalanceResponse:
    """Get user's credit balance."""
    credit_service = CreditService(db)
    stats = await credit_service.get_credit_stats(user.id)

    return CreditBalanceResponse(
        balance=stats["balance"],
        lifetime_purchased=stats["lifetime_purchased"],
    )
