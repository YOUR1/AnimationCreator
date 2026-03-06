"""User management API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.middleware import AuthenticatedUser, get_user_credits
from app.models.credit import Credit
from app.models.generation import Generation
from app.models.transaction import Transaction
from app.models.user import User

router = APIRouter(prefix="/api/users", tags=["users"])


# Response Schemas


class UserResponse(BaseModel):
    """User profile response."""

    id: int
    email: str
    name: str | None
    avatar: str | None
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Request to update user profile."""

    name: str | None = None
    avatar: str | None = None


class CreditResponse(BaseModel):
    """User credits response."""

    balance: int
    lifetime_purchased: int

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    """Transaction history item."""

    id: int
    type: str
    amount: int
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerationResponse(BaseModel):
    """Generation history item."""

    id: int
    generation_type: str
    credits_used: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    """Combined history response."""

    transactions: list[TransactionResponse]
    generations: list[GenerationResponse]


# Routes


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    user: AuthenticatedUser,
) -> UserResponse:
    """
    Get the current authenticated user's profile.

    Returns user information including email, name, avatar, and account status.
    """
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdateRequest,
    user: AuthenticatedUser,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update the current authenticated user's profile.

    Only name and avatar can be updated through this endpoint.
    """
    # Update only provided fields
    if update_data.name is not None:
        user.name = update_data.name

    if update_data.avatar is not None:
        user.avatar = update_data.avatar

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/me/credits", response_model=CreditResponse)
async def get_current_user_credits(
    user: AuthenticatedUser,
    db: AsyncSession = Depends(get_db),
) -> CreditResponse:
    """
    Get the current user's credit balance.

    Returns current balance and total lifetime credits purchased.
    """
    credits = await get_user_credits(user, db)
    return CreditResponse.model_validate(credits)


@router.get("/me/history", response_model=HistoryResponse)
async def get_current_user_history(
    user: AuthenticatedUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> HistoryResponse:
    """
    Get the current user's transaction and generation history.

    Returns both credit transactions and generation jobs, ordered by most recent.
    """
    # Validate pagination
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100",
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be non-negative",
        )

    # Fetch transactions
    transactions_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    transactions = transactions_result.scalars().all()

    # Fetch generations
    generations_result = await db.execute(
        select(Generation)
        .where(Generation.user_id == user.id)
        .order_by(Generation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    generations = generations_result.scalars().all()

    return HistoryResponse(
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
        generations=[GenerationResponse.model_validate(g) for g in generations],
    )
