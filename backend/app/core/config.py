"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class CreditCosts:
    """Credit cost definitions for generation operations.

    These values define how many credits each operation costs.
    Adjust these values to control pricing.

    Pricing rationale (targeting 80%+ profit margin):
    - fal.ai FLUX Pro image: ~$0.04/image → 1 credit (~95% margin)
    - fal.ai Kling Video (5s): ~$0.49/video → 4 credits (~84% margin)
    - Average credit value after Stripe fees: ~$0.75/credit
    """

    # Generation costs
    CHARACTER_GENERATION: int = 1  # ~$0.04 cost, ~$0.75 revenue = 95% margin
    ANIMATION_GENERATION: int = 4  # ~$0.49 cost, ~$3.00 revenue = 84% margin

    # Convenience mapping for dynamic lookups
    COSTS: dict[str, int] = {
        "character_generation": 1,
        "animation_generation": 4,
    }

    @classmethod
    def get_cost(cls, operation: str) -> int:
        """Get the credit cost for an operation.

        Args:
            operation: The operation name (e.g., 'character_generation').

        Returns:
            The credit cost for the operation.

        Raises:
            ValueError: If the operation is unknown.
        """
        cost = cls.COSTS.get(operation)
        if cost is None:
            raise ValueError(f"Unknown operation: {operation}")
        return cost


# Export credit costs for backwards compatibility
CREDIT_COSTS = CreditCosts.COSTS


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AnimationCreator"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Database
    database_url: str = "postgresql+asyncpg://localhost/animation_creator"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800  # 30 minutes

    # JWT Authentication
    jwt_secret_key: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS (stored as comma-separated string, accessed via property)
    cors_origins_str: str = "http://localhost:3000,http://localhost:5173"
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    # URLs
    api_url: str = "http://localhost:3131"
    frontend_url: str = "http://localhost:3000"

    # OAuth Providers
    google_client_id: str = ""
    google_client_secret: str = ""

    github_client_id: str = ""
    github_client_secret: str = ""

    discord_client_id: str = ""
    discord_client_secret: str = ""

    @property
    def google_redirect_uri(self) -> str:
        """Generate Google OAuth redirect URI."""
        return f"{self.api_url}/api/auth/oauth/google/callback"

    @property
    def github_redirect_uri(self) -> str:
        """Generate GitHub OAuth redirect URI."""
        return f"{self.api_url}/api/auth/oauth/github/callback"

    @property
    def discord_redirect_uri(self) -> str:
        """Generate Discord OAuth redirect URI."""
        return f"{self.api_url}/api/auth/oauth/discord/callback"

    # Stripe (for credits/payments)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_10: str = ""  # 10 credits - $9.99
    stripe_price_id_30: str = ""  # 30 credits - $24.99
    stripe_price_id_100: str = ""  # 100 credits - $74.99
    stripe_price_id_500: str = ""  # 500 credits - $299.99

    # Redis (for session management)
    redis_url: str = "redis://localhost:6379/0"

    # Celery worker settings
    celery_worker_concurrency: int = 2  # Max concurrent tasks (keep <= 10 for FAL API limit)

    # Sentry (error tracking - optional)
    sentry_dsn: str | None = None

    # Credits
    default_credits_on_signup: int = 0

    @property
    def async_database_url(self) -> str:
        """Ensure the database URL uses asyncpg driver."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_credit_cost(operation: str) -> int:
    """Get the credit cost for an operation.

    Args:
        operation: The operation name (e.g., 'character_generation').

    Returns:
        The credit cost for the operation.
    """
    return CreditCosts.get_cost(operation)
