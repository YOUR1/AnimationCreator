"""API routes and endpoints."""

from app.api.animations import router as animations_router
from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.characters import router as characters_router
from app.api.generate import router as generate_router
from app.api.users import router as users_router

__all__ = [
    "animations_router",
    "assets_router",
    "auth_router",
    "billing_router",
    "characters_router",
    "generate_router",
    "users_router",
]
