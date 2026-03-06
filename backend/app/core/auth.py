"""Authentication utilities for JWT tokens, password hashing, and OAuth."""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from urllib.parse import urlencode

import bcrypt
import httpx
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()


class TokenType(str, Enum):
    """Types of JWT tokens."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenData(BaseModel):
    """Data extracted from JWT token."""

    user_id: int
    email: str
    token_type: TokenType
    exp: datetime


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


# Password Hashing


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash.

    Returns:
        Hashed password string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to check against.

    Returns:
        True if password matches, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# JWT Token Management


def create_access_token(
    user_id: int,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's database ID.
        email: User's email address.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT access token.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    expire = datetime.now(UTC) + expires_delta

    to_encode: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "type": TokenType.ACCESS.value,
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    user_id: int,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User's database ID.
        email: User's email address.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT refresh token.
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)

    expire = datetime.now(UTC) + expires_delta

    to_encode: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "type": TokenType.REFRESH.value,
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_token_pair(user_id: int, email: str) -> TokenPair:
    """
    Create both access and refresh tokens.

    Args:
        user_id: User's database ID.
        email: User's email address.

    Returns:
        TokenPair containing both tokens.
    """
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id, email)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


def decode_token(token: str) -> TokenData | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string.

    Returns:
        TokenData if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = int(payload.get("sub", 0))
        email = payload.get("email", "")
        token_type = TokenType(payload.get("type", TokenType.ACCESS.value))
        exp = datetime.fromtimestamp(payload.get("exp", 0), tz=UTC)

        if not user_id or not email:
            return None

        return TokenData(
            user_id=user_id,
            email=email,
            token_type=token_type,
            exp=exp,
        )
    except (JWTError, ValueError):
        return None


def verify_access_token(token: str) -> TokenData | None:
    """
    Verify an access token specifically.

    Args:
        token: JWT access token string.

    Returns:
        TokenData if valid access token, None otherwise.
    """
    token_data = decode_token(token)
    if token_data and token_data.token_type == TokenType.ACCESS:
        return token_data
    return None


def verify_refresh_token(token: str) -> TokenData | None:
    """
    Verify a refresh token specifically.

    Args:
        token: JWT refresh token string.

    Returns:
        TokenData if valid refresh token, None otherwise.
    """
    token_data = decode_token(token)
    if token_data and token_data.token_type == TokenType.REFRESH:
        return token_data
    return None


# OAuth Provider Handlers (Stubs)


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""

    GOOGLE = "google"
    GITHUB = "github"
    DISCORD = "discord"


class OAuthUserInfo(BaseModel):
    """User information from OAuth provider."""

    provider: OAuthProvider
    provider_user_id: str
    email: str
    name: str | None = None
    avatar: str | None = None


class OAuthError(Exception):
    """Exception raised when OAuth authentication fails."""

    def __init__(self, message: str) -> None:
        """Initialize OAuth error with message."""
        self.message = message
        super().__init__(self.message)


async def get_google_auth_url(state: str | None = None) -> str:
    """
    Get Google OAuth authorization URL.

    Args:
        state: Optional state parameter for CSRF protection.

    Returns:
        Authorization URL to redirect user to.
    """
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def handle_google_callback(code: str) -> OAuthUserInfo:
    """
    Handle Google OAuth callback.

    Args:
        code: Authorization code from Google.

    Returns:
        User information from Google.

    Raises:
        OAuthError: If token exchange or user info retrieval fails.
    """
    async with httpx.AsyncClient() as client:
        # Exchange authorization code for access token
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
        )

        if token_response.status_code != 200:
            raise OAuthError(
                f"Failed to exchange Google authorization code: {token_response.text}"
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise OAuthError("No access token received from Google")

        # Get user information
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise OAuthError(
                f"Failed to get Google user info: {user_response.text}"
            )

        user_data = user_response.json()

        return OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id=str(user_data.get("id")),
            email=user_data.get("email", ""),
            name=user_data.get("name"),
            avatar=user_data.get("picture"),
        )


async def get_github_auth_url(state: str | None = None) -> str:
    """
    Get GitHub OAuth authorization URL.

    Args:
        state: Optional state parameter for CSRF protection.

    Returns:
        Authorization URL to redirect user to.
    """
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "user:email read:user",
    }
    if state:
        params["state"] = state

    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


async def handle_github_callback(code: str) -> OAuthUserInfo:
    """
    Handle GitHub OAuth callback.

    Args:
        code: Authorization code from GitHub.

    Returns:
        User information from GitHub.

    Raises:
        OAuthError: If token exchange or user info retrieval fails.
    """
    async with httpx.AsyncClient() as client:
        # Exchange authorization code for access token
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise OAuthError(
                f"Failed to exchange GitHub authorization code: {token_response.text}"
            )

        token_data = token_response.json()

        if "error" in token_data:
            raise OAuthError(
                f"GitHub OAuth error: {token_data.get('error_description', token_data['error'])}"
            )

        access_token = token_data.get("access_token")

        if not access_token:
            raise OAuthError("No access token received from GitHub")

        # Get user information
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if user_response.status_code != 200:
            raise OAuthError(
                f"Failed to get GitHub user info: {user_response.text}"
            )

        user_data = user_response.json()

        # GitHub may not return email in profile if private, fetch from emails endpoint
        email = user_data.get("email")
        if not email:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if emails_response.status_code == 200:
                emails = emails_response.json()
                # Find primary email or first verified email
                for email_data in emails:
                    if email_data.get("primary") and email_data.get("verified"):
                        email = email_data.get("email")
                        break
                if not email:
                    for email_data in emails:
                        if email_data.get("verified"):
                            email = email_data.get("email")
                            break

        if not email:
            raise OAuthError("Could not retrieve email from GitHub")

        return OAuthUserInfo(
            provider=OAuthProvider.GITHUB,
            provider_user_id=str(user_data.get("id")),
            email=email,
            name=user_data.get("name") or user_data.get("login"),
            avatar=user_data.get("avatar_url"),
        )


async def get_discord_auth_url(state: str | None = None) -> str:
    """
    Get Discord OAuth authorization URL.

    Args:
        state: Optional state parameter for CSRF protection.

    Returns:
        Authorization URL to redirect user to.
    """
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify email",
    }
    if state:
        params["state"] = state

    return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"


async def handle_discord_callback(code: str) -> OAuthUserInfo:
    """
    Handle Discord OAuth callback.

    Args:
        code: Authorization code from Discord.

    Returns:
        User information from Discord.

    Raises:
        OAuthError: If token exchange or user info retrieval fails.
    """
    async with httpx.AsyncClient() as client:
        # Exchange authorization code for access token
        token_response = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.discord_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            raise OAuthError(
                f"Failed to exchange Discord authorization code: {token_response.text}"
            )

        token_data = token_response.json()

        if "error" in token_data:
            raise OAuthError(
                f"Discord OAuth error: {token_data.get('error_description', token_data['error'])}"
            )

        access_token = token_data.get("access_token")

        if not access_token:
            raise OAuthError("No access token received from Discord")

        # Get user information
        user_response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise OAuthError(
                f"Failed to get Discord user info: {user_response.text}"
            )

        user_data = user_response.json()

        email = user_data.get("email")
        if not email:
            raise OAuthError("Could not retrieve email from Discord")

        # Build Discord avatar URL if avatar hash exists
        avatar_url = None
        avatar_hash = user_data.get("avatar")
        user_id = user_data.get("id")
        if avatar_hash and user_id:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"

        return OAuthUserInfo(
            provider=OAuthProvider.DISCORD,
            provider_user_id=str(user_id),
            email=email,
            name=user_data.get("global_name") or user_data.get("username"),
            avatar=avatar_url,
        )


# Session Management Utilities


class SessionManager:
    """
    Manages user sessions with optional Redis backend.

    For simple deployments, JWT tokens are stateless.
    For enhanced security, sessions can be stored in Redis for:
    - Token revocation
    - Concurrent session limits
    - Session activity tracking
    """

    def __init__(self) -> None:
        """Initialize session manager."""
        # TODO: Initialize Redis connection if configured
        self._redis_enabled = False

    async def create_session(self, user_id: int, token_data: dict[str, Any]) -> str:
        """
        Create a new session.

        Args:
            user_id: User's database ID.
            token_data: Additional session data to store.

        Returns:
            Session ID.
        """
        # For now, sessions are stateless (JWT-based)
        # TODO: Implement Redis session storage
        return f"session_{user_id}"

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Get session data.

        Args:
            session_id: Session identifier.

        Returns:
            Session data if exists, None otherwise.
        """
        # TODO: Implement Redis session retrieval
        return None

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a session.

        Args:
            session_id: Session identifier to revoke.

        Returns:
            True if session was revoked, False if not found.
        """
        # TODO: Implement Redis session revocation
        return True

    async def revoke_all_sessions(self, user_id: int) -> int:
        """
        Revoke all sessions for a user.

        Args:
            user_id: User's database ID.

        Returns:
            Number of sessions revoked.
        """
        # TODO: Implement Redis bulk session revocation
        return 0


# Global session manager instance
session_manager = SessionManager()
