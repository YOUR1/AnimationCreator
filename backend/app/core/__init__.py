"""Core application components."""

from app.core.auth import (
    TokenData,
    TokenPair,
    TokenType,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)
from app.core.config import Settings, get_settings
from app.core.database import (
    Base,
    DbSession,
    close_db,
    get_db,
    get_db_context,
    init_db,
)
from app.core.middleware import (
    AuthenticatedUser,
    AuthenticationError,
    CurrentUser,
    InsufficientCreditsError,
    RequireCredits,
    get_current_user,
    get_user_credits,
    require_auth,
    require_credits,
)
from app.core.storage_config import (
    StorageSettings,
    get_storage_settings,
    get_s3_client,
    verify_bucket_access,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Database
    "Base",
    "DbSession",
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
    # Auth
    "TokenType",
    "TokenData",
    "TokenPair",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "decode_token",
    "verify_access_token",
    "verify_refresh_token",
    # Middleware
    "get_current_user",
    "require_auth",
    "require_credits",
    "get_user_credits",
    "RequireCredits",
    "CurrentUser",
    "AuthenticatedUser",
    "AuthenticationError",
    "InsufficientCreditsError",
    # Storage
    "StorageSettings",
    "get_storage_settings",
    "get_s3_client",
    "verify_bucket_access",
]
