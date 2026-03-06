"""Stripe API configuration and product definitions.

This module handles Stripe API initialization and defines the credit pack
products available for purchase.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import stripe
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class StripeMode(Enum):
    """Stripe API mode."""
    TEST = "test"
    LIVE = "live"


@dataclass(frozen=True)
class CreditPack:
    """Represents a credit pack product."""
    id: str
    credits: int
    price_cents: int
    name: str
    description: str
    stripe_price_id: Optional[str] = None

    @property
    def price_dollars(self) -> float:
        """Get price in dollars."""
        return self.price_cents / 100

    @property
    def price_per_credit(self) -> float:
        """Get price per credit in dollars."""
        return self.price_dollars / self.credits


# Credit pack definitions
CREDIT_PACKS: dict[str, CreditPack] = {
    "pack_10": CreditPack(
        id="pack_10",
        credits=10,
        price_cents=999,
        name="Starter Pack",
        description="10 credits - Perfect for trying out AnimationCreator",
    ),
    "pack_30": CreditPack(
        id="pack_30",
        credits=30,
        price_cents=2499,
        name="Creator Pack",
        description="30 credits - Great for regular creators",
    ),
    "pack_100": CreditPack(
        id="pack_100",
        credits=100,
        price_cents=7499,
        name="Pro Pack",
        description="100 credits - Best value for professionals",
    ),
    "pack_500": CreditPack(
        id="pack_500",
        credits=500,
        price_cents=29999,
        name="Studio Pack",
        description="500 credits - Maximum savings for studios",
    ),
}


class StripeConfig:
    """Manages Stripe API configuration and initialization."""

    _initialized: bool = False
    _mode: Optional[StripeMode] = None

    def __init__(self):
        """Initialize Stripe configuration."""
        self._api_key: Optional[str] = None
        self._webhook_secret: Optional[str] = None
        self._price_ids: dict[str, str] = {}

    @classmethod
    def initialize(cls) -> "StripeConfig":
        """Initialize Stripe API with environment configuration.

        Returns:
            StripeConfig: Configured Stripe instance.

        Raises:
            ValueError: If required environment variables are missing.
        """
        config = cls()

        # Load API key
        config._api_key = os.getenv("STRIPE_SECRET_KEY")
        if not config._api_key:
            raise ValueError(
                "STRIPE_SECRET_KEY not found. Please set it in your .env file.\n"
                "Get your key from: https://dashboard.stripe.com/apikeys"
            )

        # Set the API key globally for stripe module
        stripe.api_key = config._api_key

        # Load webhook secret
        config._webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not config._webhook_secret:
            logger.warning(
                "STRIPE_WEBHOOK_SECRET not found. Webhook signature verification "
                "will fail. Set it in your .env file."
            )

        # Determine mode from API key
        if config._api_key.startswith("sk_test_"):
            cls._mode = StripeMode.TEST
            logger.info("Stripe initialized in TEST mode")
        elif config._api_key.startswith("sk_live_"):
            cls._mode = StripeMode.LIVE
            logger.info("Stripe initialized in LIVE mode")
        else:
            logger.warning("Unable to determine Stripe mode from API key")

        # Load price IDs from environment
        config._price_ids = {
            "pack_10": os.getenv("STRIPE_PRICE_ID_10", ""),
            "pack_30": os.getenv("STRIPE_PRICE_ID_30", ""),
            "pack_100": os.getenv("STRIPE_PRICE_ID_100", ""),
            "pack_500": os.getenv("STRIPE_PRICE_ID_500", ""),
        }

        cls._initialized = True
        return config

    @property
    def api_key(self) -> str:
        """Get Stripe API key."""
        if not self._api_key:
            raise ValueError("Stripe not initialized. Call initialize() first.")
        return self._api_key

    @property
    def webhook_secret(self) -> Optional[str]:
        """Get Stripe webhook secret."""
        return self._webhook_secret

    @property
    def is_test_mode(self) -> bool:
        """Check if running in test mode."""
        return self._mode == StripeMode.TEST

    @property
    def is_live_mode(self) -> bool:
        """Check if running in live mode."""
        return self._mode == StripeMode.LIVE

    def get_price_id(self, pack_id: str) -> Optional[str]:
        """Get Stripe Price ID for a credit pack.

        Args:
            pack_id: The credit pack identifier (e.g., 'pack_10').

        Returns:
            The Stripe Price ID or None if not configured.
        """
        return self._price_ids.get(pack_id) or None

    def get_pack_by_price_id(self, price_id: str) -> Optional[CreditPack]:
        """Get credit pack by Stripe Price ID.

        Args:
            price_id: The Stripe Price ID.

        Returns:
            The corresponding CreditPack or None if not found.
        """
        for pack_id, pid in self._price_ids.items():
            if pid == price_id:
                return CREDIT_PACKS.get(pack_id)
        return None


def get_credit_pack(pack_id: str) -> Optional[CreditPack]:
    """Get a credit pack by ID.

    Args:
        pack_id: The pack identifier (e.g., 'pack_10', 'pack_30').

    Returns:
        The CreditPack or None if not found.
    """
    return CREDIT_PACKS.get(pack_id)


def list_credit_packs() -> list[CreditPack]:
    """List all available credit packs.

    Returns:
        List of credit packs sorted by credit amount.
    """
    return sorted(CREDIT_PACKS.values(), key=lambda p: p.credits)


async def create_checkout_session(
    user_id: str,
    user_email: str,
    pack_id: str,
    success_url: str,
    cancel_url: str,
    stripe_customer_id: Optional[str] = None,
) -> stripe.checkout.Session:
    """Create a Stripe Checkout session for credit purchase.

    Args:
        user_id: Internal user ID.
        user_email: User's email address.
        pack_id: Credit pack identifier.
        success_url: URL to redirect on successful payment.
        cancel_url: URL to redirect on cancelled payment.
        stripe_customer_id: Optional existing Stripe customer ID.

    Returns:
        Stripe Checkout Session object.

    Raises:
        ValueError: If pack_id is invalid or price_id is not configured.
    """
    pack = get_credit_pack(pack_id)
    if not pack:
        raise ValueError(f"Invalid credit pack: {pack_id}")

    config = StripeConfig.initialize()
    price_id = config.get_price_id(pack_id)

    if not price_id:
        raise ValueError(
            f"Stripe Price ID not configured for {pack_id}. "
            "Please set STRIPE_PRICE_ID_* environment variables."
        )

    session_params: dict = {
        "mode": "payment",
        "payment_method_types": ["card"],
        "line_items": [
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {
            "user_id": user_id,
            "pack_id": pack_id,
            "credits": str(pack.credits),
        },
        "payment_intent_data": {
            "metadata": {
                "user_id": user_id,
                "pack_id": pack_id,
                "credits": str(pack.credits),
            },
        },
    }

    if stripe_customer_id:
        session_params["customer"] = stripe_customer_id
    else:
        session_params["customer_email"] = user_email
        session_params["customer_creation"] = "always"

    session = stripe.checkout.Session.create(**session_params)

    logger.info(
        "Created checkout session %s for user %s, pack %s",
        session.id,
        user_id,
        pack_id,
    )

    return session


async def create_customer_portal_session(
    stripe_customer_id: str,
    return_url: str,
) -> stripe.billing_portal.Session:
    """Create a Stripe Customer Portal session.

    Args:
        stripe_customer_id: The Stripe customer ID.
        return_url: URL to return to after portal session.

    Returns:
        Stripe Billing Portal Session object.
    """
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )

    logger.info(
        "Created customer portal session for customer %s",
        stripe_customer_id,
    )

    return session


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    webhook_secret: str,
) -> stripe.Event:
    """Verify and construct a Stripe webhook event.

    Args:
        payload: Raw request body bytes.
        signature: Stripe-Signature header value.
        webhook_secret: Webhook endpoint secret.

    Returns:
        Verified Stripe Event object.

    Raises:
        stripe.error.SignatureVerificationError: If signature is invalid.
    """
    event = stripe.Webhook.construct_event(
        payload,
        signature,
        webhook_secret,
    )
    return event
