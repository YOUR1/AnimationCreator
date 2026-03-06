"""Authentication API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    OAuthError,
    OAuthProvider,
    OAuthUserInfo,
    TokenPair,
    create_token_pair,
    get_discord_auth_url,
    get_github_auth_url,
    get_google_auth_url,
    handle_discord_callback,
    handle_github_callback,
    handle_google_callback,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.core.middleware import AuthenticatedUser
from app.models.credit import Credit
from app.models.transaction import Transaction, TransactionType
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


# Request/Response Schemas


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class AuthResponse(BaseModel):
    """Authentication response with tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    """User information in auth response."""

    id: int
    email: str
    name: str | None
    avatar: str | None
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# Routes


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Register a new user account.

    Creates a new user with the provided email and password.
    Returns authentication tokens on successful registration.
    """
    # Check if email already exists
    existing_user = await db.execute(
        select(User).where(User.email == request.email.lower())
    )
    if existing_user.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create new user
    user = User(
        email=request.email.lower(),
        hashed_password=hash_password(request.password),
        name=request.name,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()  # Get the user ID

    # Create initial credits
    credits = Credit(
        user_id=user.id,
        balance=settings.default_credits_on_signup,
        lifetime_purchased=0,
    )
    db.add(credits)

    # Record signup bonus transaction
    if settings.default_credits_on_signup > 0:
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.SIGNUP.value,
            amount=settings.default_credits_on_signup,
            description="Welcome bonus credits",
        )
        db.add(transaction)

    await db.commit()
    await db.refresh(user)

    # Generate tokens
    token_pair = create_token_pair(user.id, user.email)

    return AuthResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Authenticate a user and return tokens.

    Validates email and password, returns access and refresh tokens.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email.lower())
    )
    user = result.scalar_one_or_none()

    # Validate credentials
    if user is None or user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Generate tokens
    token_pair = create_token_pair(user.id, user.email)

    return AuthResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    user: AuthenticatedUser,
    response: Response,
) -> MessageResponse:
    """
    Log out the current user.

    For stateless JWT auth, this is mostly a no-op on the server side.
    The client should discard the tokens.

    In a Redis-backed session implementation, this would revoke the session.
    """
    # TODO: If using Redis sessions, revoke the session here
    # await session_manager.revoke_session(session_id)

    return MessageResponse(message="Successfully logged out")


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Refresh an access token using a refresh token.

    Returns a new token pair if the refresh token is valid.
    """
    # Verify refresh token
    token_data = verify_refresh_token(request.refresh_token)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    # Generate new tokens
    token_pair = create_token_pair(user.id, user.email)

    return AuthResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user: AuthenticatedUser,
) -> UserResponse:
    """
    Get the current authenticated user's information.

    This is a convenience endpoint that returns the same data as /api/users/me.
    """
    return UserResponse.model_validate(user)


# OAuth Schemas


class OAuthAuthorizationResponse(BaseModel):
    """OAuth authorization URL response."""

    authorization_url: str


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request with authorization code."""

    code: str
    state: str | None = None


# OAuth Routes


@router.get("/oauth/{provider}/authorize", response_model=OAuthAuthorizationResponse)
async def oauth_authorize(
    provider: OAuthProvider,
    state: str | None = None,
) -> OAuthAuthorizationResponse:
    """
    Get OAuth authorization URL for a provider.

    Redirects user to the OAuth provider's login page.
    """
    if provider == OAuthProvider.GOOGLE:
        url = await get_google_auth_url(state)
    elif provider == OAuthProvider.GITHUB:
        url = await get_github_auth_url(state)
    elif provider == OAuthProvider.DISCORD:
        url = await get_discord_auth_url(state)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    return OAuthAuthorizationResponse(authorization_url=url)


@router.post("/oauth/{provider}/callback", response_model=AuthResponse)
async def oauth_callback(
    provider: OAuthProvider,
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Handle OAuth callback from provider.

    Exchanges authorization code for user info and creates/logs in user.
    """
    try:
        if provider == OAuthProvider.GOOGLE:
            oauth_user = await handle_google_callback(request.code)
        elif provider == OAuthProvider.GITHUB:
            oauth_user = await handle_github_callback(request.code)
        elif provider == OAuthProvider.DISCORD:
            oauth_user = await handle_discord_callback(request.code)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            )
    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message),
        )

    # Check if user exists by OAuth ID
    result = await db.execute(
        select(User).where(
            User.oauth_provider == oauth_user.provider.value,
            User.oauth_id == oauth_user.provider_user_id,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Check if email already exists (user might have signed up with password)
        result = await db.execute(
            select(User).where(User.email == oauth_user.email.lower())
        )
        user = result.scalar_one_or_none()

        if user is not None:
            # Link OAuth to existing account
            user.oauth_provider = oauth_user.provider.value
            user.oauth_id = oauth_user.provider_user_id
            if oauth_user.avatar and not user.avatar:
                user.avatar = oauth_user.avatar
            if oauth_user.name and not user.name:
                user.name = oauth_user.name
            user.is_verified = True
        else:
            # Create new user
            user = User(
                email=oauth_user.email.lower(),
                name=oauth_user.name,
                avatar=oauth_user.avatar,
                oauth_provider=oauth_user.provider.value,
                oauth_id=oauth_user.provider_user_id,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()

            # Create initial credits for new user
            credits = Credit(
                user_id=user.id,
                balance=settings.default_credits_on_signup,
                lifetime_purchased=0,
            )
            db.add(credits)

            # Record signup bonus transaction
            if settings.default_credits_on_signup > 0:
                transaction = Transaction(
                    user_id=user.id,
                    type=TransactionType.SIGNUP.value,
                    amount=settings.default_credits_on_signup,
                    description="Welcome bonus credits",
                )
                db.add(transaction)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    await db.commit()
    await db.refresh(user)

    # Generate tokens
    token_pair = create_token_pair(user.id, user.email)

    return AuthResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/oauth/{provider}/callback")
async def oauth_callback_redirect(
    provider: OAuthProvider,
    code: str,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Handle OAuth callback redirect from provider.

    This GET endpoint receives the redirect from OAuth providers,
    processes the authorization code, and redirects to the frontend
    with tokens.
    """
    try:
        if provider == OAuthProvider.GOOGLE:
            oauth_user = await handle_google_callback(code)
        elif provider == OAuthProvider.GITHUB:
            oauth_user = await handle_github_callback(code)
        elif provider == OAuthProvider.DISCORD:
            oauth_user = await handle_discord_callback(code)
        else:
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=unsupported_provider"
            )
    except OAuthError as e:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error={e.message}"
        )

    # Check if user exists by OAuth ID
    result = await db.execute(
        select(User).where(
            User.oauth_provider == oauth_user.provider.value,
            User.oauth_id == oauth_user.provider_user_id,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == oauth_user.email.lower())
        )
        user = result.scalar_one_or_none()

        if user is not None:
            # Link OAuth to existing account
            user.oauth_provider = oauth_user.provider.value
            user.oauth_id = oauth_user.provider_user_id
            if oauth_user.avatar and not user.avatar:
                user.avatar = oauth_user.avatar
            if oauth_user.name and not user.name:
                user.name = oauth_user.name
            user.is_verified = True
        else:
            # Create new user
            user = User(
                email=oauth_user.email.lower(),
                name=oauth_user.name,
                avatar=oauth_user.avatar,
                oauth_provider=oauth_user.provider.value,
                oauth_id=oauth_user.provider_user_id,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()

            # Create initial credits for new user
            credits = Credit(
                user_id=user.id,
                balance=settings.default_credits_on_signup,
                lifetime_purchased=0,
            )
            db.add(credits)

            # Record signup bonus transaction
            if settings.default_credits_on_signup > 0:
                transaction = Transaction(
                    user_id=user.id,
                    type=TransactionType.SIGNUP.value,
                    amount=settings.default_credits_on_signup,
                    description="Welcome bonus credits",
                )
                db.add(transaction)

    if not user.is_active:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=account_deactivated"
        )

    await db.commit()
    await db.refresh(user)

    # Generate tokens
    token_pair = create_token_pair(user.id, user.email)

    # Create redirect response with cookies
    response = RedirectResponse(
        url=f"{settings.frontend_url}/dashboard",
        status_code=302
    )

    # Set cookies for auth
    response.set_cookie(
        key="access_token",
        value=token_pair.access_token,
        max_age=60 * 60 * 24 * 7,  # 7 days
        httponly=False,  # Allow JS access for API calls
        samesite="lax",
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=token_pair.refresh_token,
        max_age=60 * 60 * 24 * 7,  # 7 days
        httponly=False,
        samesite="lax",
        path="/"
    )

    return response
