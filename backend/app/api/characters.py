"""Characters API routes for managing user characters."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.middleware import AuthenticatedUser, require_auth
from app.models.character import Character
from app.models.user import User

router = APIRouter(prefix="/api/characters", tags=["characters"])


# Response Schemas


class CharacterResponse(BaseModel):
    """Character response schema."""

    id: str
    user_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    style: str
    prompt: str
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, character: Character) -> "CharacterResponse":
        """Convert database model to response."""
        # Derive status from whether image_url exists
        status = "completed" if character.image_url else "pending"
        return cls(
            id=str(character.id),
            user_id=str(character.user_id),
            name=character.name,
            description=character.prompt,  # Use prompt as description
            style=character.style,
            prompt=character.prompt,
            image_url=character.image_url,
            thumbnail_url=character.thumbnail_url,
            status=status,
            created_at=character.created_at.isoformat(),
            updated_at=character.updated_at.isoformat(),
        )


class PaginatedCharactersResponse(BaseModel):
    """Paginated characters response."""

    items: list[CharacterResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# Routes


@router.get("", response_model=PaginatedCharactersResponse)
async def list_characters(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", description="Sort order (asc or desc)"),
    style: Optional[str] = Query(default=None, description="Filter by style"),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCharactersResponse:
    """
    List all characters for the authenticated user.

    Supports pagination, sorting, and filtering by style.
    """
    # Build base query
    query = select(Character).where(Character.user_id == user.id)

    # Apply style filter
    if style:
        query = query.where(Character.style == style)

    # Apply sorting
    sort_column = getattr(Character, sort_by, Character.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Get total count
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    characters = result.scalars().all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedCharactersResponse(
        items=[CharacterResponse.from_model(c) for c in characters],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> CharacterResponse:
    """
    Get a specific character by ID.

    Only returns characters owned by the authenticated user.
    """
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == user.id,
        )
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    return CharacterResponse.from_model(character)


@router.delete("/{character_id}", response_model=MessageResponse)
async def delete_character(
    character_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Delete a character by ID.

    Only allows deletion of characters owned by the authenticated user.
    Also deletes all associated animations.
    """
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == user.id,
        )
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    await db.delete(character)
    await db.commit()

    return MessageResponse(message="Character deleted successfully")


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: int,
    name: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> CharacterResponse:
    """
    Update a character's metadata.

    Only allows updating characters owned by the authenticated user.
    """
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == user.id,
        )
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    if name is not None:
        character.name = name
    if is_favorite is not None:
        character.is_favorite = is_favorite

    await db.commit()
    await db.refresh(character)

    return CharacterResponse.from_model(character)
