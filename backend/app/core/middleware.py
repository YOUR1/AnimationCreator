"""Authentication middleware for FastAPI routes."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_access_token
from app.core.database import get_db
from app.models.credit import Credit
from app.models.user import User

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InsufficientCreditsError(HTTPException):
    """Raised when user doesn't have enough credits."""

    def __init__(self, required: int, available: int) -> None:
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "insufficient_credits",
                "required": required,
                "available": available,
                "message": f"This operation requires {required} credits, but you only have {available}.",
            },
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Get the current authenticated user, or None if not authenticated.

    This dependency does NOT raise an error if the user is not authenticated.
    Use require_auth() if authentication is required.

    Args:
        request: FastAPI request object.
        credentials: Bearer token credentials.
        db: Database session.

    Returns:
        User object if authenticated, None otherwise.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    token_data = verify_access_token(token)

    if token_data is None:
        return None

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    # Store user in request state for later access
    request.state.user = user
    return user


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Require authentication and return the current user.

    Raises HTTPException 401 if not authenticated.

    Args:
        request: FastAPI request object.
        credentials: Bearer token credentials.
        db: Database session.

    Returns:
        Authenticated User object.

    Raises:
        AuthenticationError: If user is not authenticated.
    """
    if credentials is None:
        raise AuthenticationError("No authorization header provided")

    token = credentials.credentials
    token_data = verify_access_token(token)

    if token_data is None:
        raise AuthenticationError("Invalid or expired token")

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    # Store user in request state for later access
    request.state.user = user
    return user


async def get_user_credits(user: User, db: AsyncSession) -> Credit:
    """
    Get the credit record for a user.

    Args:
        user: User object.
        db: Database session.

    Returns:
        Credit object for the user.
    """
    result = await db.execute(select(Credit).where(Credit.user_id == user.id))
    credits = result.scalar_one_or_none()

    if credits is None:
        # Create credit record if it doesn't exist
        credits = Credit(user_id=user.id, balance=0, lifetime_purchased=0)
        db.add(credits)
        await db.flush()

    return credits


class RequireCredits:
    """
    Dependency class that requires a specific amount of credits.

    Usage:
        @app.post("/generate")
        async def generate(
            user: User = Depends(require_auth),
            _: None = Depends(RequireCredits(5)),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    """

    def __init__(self, amount: int) -> None:
        """
        Initialize the credits requirement.

        Args:
            amount: Number of credits required.
        """
        self.amount = amount

    async def __call__(
        self,
        request: Request,
        user: User = Depends(require_auth),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        """
        Check if user has sufficient credits.

        Args:
            request: FastAPI request object.
            user: Authenticated user.
            db: Database session.

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits.
        """
        credits = await get_user_credits(user, db)

        if not credits.has_sufficient_credits(self.amount):
            raise InsufficientCreditsError(
                required=self.amount,
                available=credits.balance,
            )

        # Store credits in request state for later use
        request.state.credits = credits


async def require_credits(
    request: Request,
    amount: int,
    db: AsyncSession,
) -> None:
    """
    Standalone function to check if user has sufficient credits.

    This can be called directly in route handlers when the amount
    is determined dynamically.

    Args:
        request: FastAPI request object (must have user in state).
        amount: Number of credits required.
        db: Database session.

    Raises:
        AuthenticationError: If no user in request state.
        InsufficientCreditsError: If user doesn't have enough credits.
    """
    user: User | None = getattr(request.state, "user", None)
    if user is None:
        raise AuthenticationError("User not authenticated")

    credits = await get_user_credits(user, db)

    if not credits.has_sufficient_credits(amount):
        raise InsufficientCreditsError(
            required=amount,
            available=credits.balance,
        )

    request.state.credits = credits


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User | None, Depends(get_current_user)]
AuthenticatedUser = Annotated[User, Depends(require_auth)]
