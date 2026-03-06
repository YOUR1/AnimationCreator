"""Animations API routes for managing character animations."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.middleware import require_auth
from app.models.animation import Animation
from app.models.character import Character
from app.models.user import User

router = APIRouter(prefix="/api/animations", tags=["animations"])


# Response Schemas


class AnimationResponse(BaseModel):
    """Animation response schema."""

    id: str
    character_id: str
    user_id: str
    name: str
    type: str
    video_url: Optional[str] = None
    gif_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str
    duration: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, animation: Animation, user_id: int) -> "AnimationResponse":
        """Convert database model to response."""
        return cls(
            id=str(animation.id),
            character_id=str(animation.character_id),
            user_id=str(user_id),
            name=animation.state,  # Use state as name
            type=animation.state,  # Use state as type
            video_url=animation.video_url,
            gif_url=animation.gif_url,
            thumbnail_url=animation.thumbnail_url,
            status=animation.status,
            duration=0,  # Duration not stored in model
            created_at=animation.created_at.isoformat(),
            updated_at=animation.updated_at.isoformat(),
        )


class PaginatedAnimationsResponse(BaseModel):
    """Paginated animations response."""

    items: list[AnimationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# Routes


@router.get("", response_model=PaginatedAnimationsResponse)
async def list_animations(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    character_id: Optional[int] = Query(default=None, description="Filter by character"),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", description="Sort order (asc or desc)"),
    type: Optional[str] = Query(default=None, description="Filter by animation type/state"),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> PaginatedAnimationsResponse:
    """
    List all animations for the authenticated user.

    Supports pagination, sorting, and filtering by character or type.
    """
    # Build base query - join with Character to filter by user
    query = (
        select(Animation)
        .join(Character, Animation.character_id == Character.id)
        .where(Character.user_id == user.id)
    )

    # Apply character filter
    if character_id:
        query = query.where(Animation.character_id == character_id)

    # Apply type/state filter
    if type:
        query = query.where(Animation.state == type)

    # Apply sorting
    sort_column = getattr(Animation, sort_by, Animation.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    animations = result.scalars().all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedAnimationsResponse(
        items=[AnimationResponse.from_model(a, user.id) for a in animations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{animation_id}", response_model=AnimationResponse)
async def get_animation(
    animation_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> AnimationResponse:
    """
    Get a specific animation by ID.

    Only returns animations owned by the authenticated user.
    """
    result = await db.execute(
        select(Animation)
        .join(Character, Animation.character_id == Character.id)
        .where(
            Animation.id == animation_id,
            Character.user_id == user.id,
        )
    )
    animation = result.scalar_one_or_none()

    if not animation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animation not found",
        )

    return AnimationResponse.from_model(animation, user.id)


@router.delete("/{animation_id}", response_model=MessageResponse)
async def delete_animation(
    animation_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Delete an animation by ID.

    Only allows deletion of animations owned by the authenticated user.
    """
    result = await db.execute(
        select(Animation)
        .join(Character, Animation.character_id == Character.id)
        .where(
            Animation.id == animation_id,
            Character.user_id == user.id,
        )
    )
    animation = result.scalar_one_or_none()

    if not animation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animation not found",
        )

    await db.delete(animation)
    await db.commit()

    return MessageResponse(message="Animation deleted successfully")
