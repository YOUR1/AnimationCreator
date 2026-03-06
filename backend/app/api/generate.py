"""
Generation API routes for character and animation generation.

This module provides FastAPI routes for:
- Creating character generation jobs
- Creating animation generation jobs
- Checking job status
- Streaming job progress via SSE
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import CreditCosts, get_settings
from app.core.database import get_db
from app.core.middleware import (
    AuthenticatedUser,
    InsufficientCreditsError,
    require_auth,
)
from app.models.animation import Animation
from app.models.character import Character
from app.models.generation import Generation, GenerationStatus
from app.models.user import User
from app.services.credits import CreditService, InsufficientCreditsError as CreditError
from app.services.queue import (
    Job,
    JobStatus,
    JobType,
    create_animation_job,
    create_character_job,
    get_job_status,
    get_queue_service,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/generate", tags=["generation"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CharacterGenerateRequest(BaseModel):
    """Request schema for character generation."""

    name: str = Field(
        ...,
        description="Character name",
        min_length=1,
        max_length=100,
        examples=["Luna the Explorer"],
    )
    prompt: str = Field(
        ...,
        description="Character description prompt",
        min_length=3,
        max_length=1000,
        examples=["A cute orange cat wearing a wizard hat"],
    )
    style: str = Field(
        ...,
        description="Style preset key",
        examples=["kawaii", "pixar", "realistic", "pixel", "watercolor"],
    )


class AnimationGenerateRequest(BaseModel):
    """Request schema for animation generation."""

    character_id: int = Field(
        ...,
        description="ID of the character to animate",
        gt=0,
    )
    type: str = Field(
        ...,
        description="Animation state/type to generate",
        examples=["idle", "walk", "run", "jump", "attack", "dancing", "sad", "excited", "custom"],
    )
    name: str = Field(
        ...,
        description="Name for the animation",
        min_length=1,
        max_length=200,
    )
    prompt: Optional[str] = Field(
        default=None,
        description="Custom animation description/prompt",
        max_length=1000,
    )
    duration: int = Field(
        default=5,
        description="Animation duration in seconds (5 or 10)",
        ge=5,
        le=10,
    )
    aspect_ratio: str = Field(
        default="1:1",
        description="Output aspect ratio (1:1, 16:9, or 9:16)",
    )
    negative_prompt: Optional[str] = Field(
        default=None,
        description="Elements to avoid in generation (e.g., 'shadows, blur')",
        max_length=500,
    )
    seamless_loop: bool = Field(
        default=True,
        description="Create seamless loop using ping-pong effect. Recommended when using multiple animations for smooth transitions between states.",
    )
    cfg_scale: Optional[float] = Field(
        default=None,
        description="Classifier Free Guidance scale (typically 0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    special_fx: Optional[str] = Field(
        default=None,
        description="Special effects: hug, kiss, heart_gesture, squish, expansion",
    )


class JobResponse(BaseModel):
    """Response schema for job status."""

    id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    progress: int = Field(..., description="Progress percentage 0-100")
    result: Optional[dict] = Field(default=None, description="Job result on completion")
    error: Optional[str] = Field(default=None, description="Error message on failure")
    type: str = Field(..., description="Job type")
    created_at: str = Field(..., description="Job creation timestamp")

    class Config:
        from_attributes = True


class GenerationStartResponse(BaseModel):
    """Response schema for starting a generation."""

    job_id: str = Field(..., description="Job identifier for tracking")
    message: str = Field(..., description="Status message")
    credits_used: int = Field(..., description="Credits deducted for this operation")


class CreditCheckResponse(BaseModel):
    """Response schema for credit check."""

    has_sufficient_credits: bool = Field(..., description="Whether user has enough credits")
    current_balance: int = Field(..., description="Current credit balance")
    required_credits: int = Field(..., description="Credits required for operation")


# ============================================================================
# Utility Functions
# ============================================================================


def _validate_style(style: str) -> None:
    """Validate style key against available styles."""
    valid_styles = ["kawaii", "pixar", "realistic", "pixel", "watercolor"]
    if style not in valid_styles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid style. Must be one of: {', '.join(valid_styles)}",
        )


def _validate_states(states: list[str]) -> None:
    """Validate animation state keys."""
    valid_states = ["idle", "walk", "run", "jump", "attack", "custom", "dancing", "sad", "excited"]
    invalid = [s for s in states if s not in valid_states]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid states: {', '.join(invalid)}. Must be from: {', '.join(valid_states)}",
        )


def _validate_aspect_ratio(aspect_ratio: str) -> None:
    """Validate aspect ratio."""
    valid_ratios = ["1:1", "16:9", "9:16"]
    if aspect_ratio not in valid_ratios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid aspect ratio. Must be one of: {', '.join(valid_ratios)}",
        )


def _validate_duration(duration: int) -> None:
    """Validate duration (Kling AI only supports 5 or 10 seconds)."""
    valid_durations = [5, 10]
    if duration not in valid_durations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid duration. Must be one of: {', '.join(map(str, valid_durations))}",
        )


def _validate_special_fx(special_fx: str | None) -> None:
    """Validate special effects."""
    if special_fx is None:
        return
    valid_fx = ["hug", "kiss", "heart_gesture", "squish", "expansion"]
    if special_fx not in valid_fx:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid special effect. Must be one of: {', '.join(valid_fx)}",
        )


# ============================================================================
# Routes
# ============================================================================


@router.post(
    "/character",
    response_model=GenerationStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create character generation job",
    description="Start a new character generation job using the provided prompt and style.",
    responses={
        400: {"description": "Invalid request parameters"},
        401: {"description": "Authentication required"},
        402: {"description": "Insufficient credits"},
    },
)
async def generate_character(
    request: CharacterGenerateRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> GenerationStartResponse:
    """
    Create a new character generation job.

    This endpoint:
    1. Validates the user has sufficient credits
    2. Deducts credits from the user's account
    3. Creates a generation record
    4. Queues the character generation task

    The job processes asynchronously. Use GET /api/generate/status/{jobId}
    to check progress.
    """
    # Validate style
    _validate_style(request.style)

    # Check and deduct credits
    credits_required = CreditCosts.CHARACTER_GENERATION
    credit_service = CreditService(db)

    try:
        # Create generation record first
        generation = Generation(
            user_id=user.id,
            generation_type="character",
            credits_used=credits_required,
            status=GenerationStatus.QUEUED.value,
        )
        db.add(generation)
        await db.flush()

        # Deduct credits
        await credit_service.deduct_credits(
            user_id=user.id,
            amount=credits_required,
            reason="character_generation",
            generation_id=generation.id,
        )

        # Create job and queue task
        job = await create_character_job(
            db=db,
            user_id=user.id,
            name=request.name,
            prompt=request.prompt,
            style=request.style,
            generation_id=generation.id,
        )

        # Update generation with external job ID
        generation.external_job_id = job.id
        await db.commit()

        logger.info(f"Character generation started: job={job.id}, user={user.id}")

        return GenerationStartResponse(
            job_id=job.id,
            message="Character generation started",
            credits_used=credits_required,
        )

    except CreditError as e:
        await db.rollback()
        raise InsufficientCreditsError(
            required=e.required,
            available=e.available,
        )


@router.post(
    "/animations",
    response_model=GenerationStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create animation generation job",
    description="Start animation generation for a character with specified states.",
    responses={
        400: {"description": "Invalid request parameters"},
        401: {"description": "Authentication required"},
        402: {"description": "Insufficient credits"},
        404: {"description": "Character not found"},
    },
)
async def generate_animations(
    request: AnimationGenerateRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> GenerationStartResponse:
    """
    Create a new animation generation job.

    This endpoint:
    1. Validates the character exists and belongs to the user
    2. Validates animation type and parameters
    3. Checks and deducts credits (1 credit per animation)
    4. Creates a generation record
    5. Queues the animation generation task

    The job processes asynchronously. Use GET /api/generate/status/{jobId}
    to check progress.
    """
    # Validate animation type and parameters
    _validate_states([request.type])
    _validate_aspect_ratio(request.aspect_ratio)
    _validate_duration(request.duration)
    _validate_special_fx(request.special_fx)

    # Verify character exists and belongs to user
    result = await db.execute(
        select(Character).where(
            Character.id == request.character_id,
            Character.user_id == user.id,
        )
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    if not character.image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character has no image. Generate a character first.",
        )

    # Calculate credits (1 per animation)
    credits_required = CreditCosts.ANIMATION_GENERATION
    credit_service = CreditService(db)

    try:
        # Create generation record
        generation = Generation(
            user_id=user.id,
            generation_type="animation",
            credits_used=credits_required,
            status=GenerationStatus.QUEUED.value,
        )
        db.add(generation)
        await db.flush()

        # Deduct credits
        await credit_service.deduct_credits(
            user_id=user.id,
            amount=credits_required,
            reason="animation_generation",
            generation_id=generation.id,
        )

        # Create job and queue task with all parameters
        job = await create_animation_job(
            db=db,
            user_id=user.id,
            character_id=request.character_id,
            states=[request.type],
            generation_id=generation.id,
            custom_prompt=request.prompt,
            duration=request.duration,
            aspect_ratio=request.aspect_ratio,
            negative_prompt=request.negative_prompt,
            cfg_scale=request.cfg_scale,
            special_fx=request.special_fx,
            seamless_loop=request.seamless_loop,
        )

        # Update generation with external job ID
        generation.external_job_id = job.id
        await db.commit()

        logger.info(
            f"Animation generation started: job={job.id}, user={user.id}, "
            f"character={request.character_id}, type={request.type}"
        )

        return GenerationStartResponse(
            job_id=job.id,
            message=f"Animation generation started for type '{request.type}'",
            credits_used=credits_required,
        )

    except CreditError as e:
        await db.rollback()
        raise InsufficientCreditsError(
            required=e.required,
            available=e.available,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/status/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    description="Get the current status and progress of a generation job.",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Job not found"},
    },
)
async def get_status(
    job_id: str,
    user: User = Depends(require_auth),
) -> JobResponse:
    """
    Get the status of a generation job.

    Returns the current status, progress percentage, and result (if completed)
    or error (if failed).
    """
    job = await get_job_status(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Verify job belongs to user
    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobResponse(
        id=job.id,
        status=job.status,
        progress=job.progress,
        result=job.result,
        error=job.error,
        type=job.type,
        created_at=job.created_at.isoformat(),
    )


@router.get(
    "/stream/{job_id}",
    summary="Stream job progress",
    description="Stream real-time progress updates for a generation job via SSE.",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Job not found"},
    },
)
async def stream_progress(
    job_id: str,
    user: User = Depends(require_auth),
):
    """
    Stream progress updates for a generation job using Server-Sent Events (SSE).

    The stream sends JSON events with the following format:
    ```
    data: {"job_id": "...", "progress": 50, "message": "Generating...", "timestamp": "..."}
    ```

    The stream closes when the job completes or fails.
    """
    # Verify job exists and belongs to user
    job = await get_job_status(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    async def event_generator():
        """Generate SSE events for job progress."""
        queue = get_queue_service()
        pubsub = queue.redis.pubsub()
        channel = f"job:{job_id}:progress"

        try:
            pubsub.subscribe(channel)

            # Send initial status
            current_job = await get_job_status(job_id)
            if current_job:
                yield f"data: {json.dumps({'job_id': job_id, 'progress': current_job.progress, 'status': current_job.status, 'message': 'Connected'})}\n\n"

                # If already completed/failed, send final status and close
                if current_job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    final_data = {
                        "job_id": job_id,
                        "progress": current_job.progress,
                        "status": current_job.status,
                        "result": current_job.result,
                        "error": current_job.error,
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    return

            # Listen for updates
            while True:
                message = pubsub.get_message(timeout=1.0)

                if message and message["type"] == "message":
                    yield f"data: {message['data']}\n\n"

                    # Check if job is done
                    data = json.loads(message["data"])
                    if data.get("progress") == 100 or "error" in data:
                        break

                # Heartbeat to keep connection alive
                yield f": heartbeat\n\n"

                # Check job status periodically
                current_job = await get_job_status(job_id)
                if current_job and current_job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    final_data = {
                        "job_id": job_id,
                        "progress": current_job.progress,
                        "status": current_job.status,
                        "result": current_job.result,
                        "error": current_job.error,
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    break

                await asyncio.sleep(0.5)

        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/check-credits",
    response_model=CreditCheckResponse,
    summary="Check if user has sufficient credits",
    description="Check if the user has enough credits for an operation.",
    responses={
        401: {"description": "Authentication required"},
    },
)
async def check_credits(
    operation: str = Query(
        ...,
        description="Operation type (character or animation)",
        examples=["character", "animation"],
    ),
    count: int = Query(
        default=1,
        description="Number of items to generate",
        ge=1,
        le=10,
    ),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> CreditCheckResponse:
    """
    Check if the user has sufficient credits for an operation.

    Useful for client-side validation before starting a generation.
    """
    if operation == "character":
        required = CreditCosts.CHARACTER_GENERATION * count
    elif operation == "animation":
        required = CreditCosts.ANIMATION_GENERATION * count
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid operation. Must be 'character' or 'animation'",
        )

    credit_service = CreditService(db)
    balance = await credit_service.get_credit_balance(user.id)

    return CreditCheckResponse(
        has_sufficient_credits=balance >= required,
        current_balance=balance,
        required_credits=required,
    )


@router.get(
    "/pending",
    summary="Get pending generations",
    description="Get all queued/processing generations for the current user.",
    responses={
        401: {"description": "Authentication required"},
    },
)
async def get_pending_generations(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all pending (queued or processing) generations for the current user.
    """
    result = await db.execute(
        select(Generation)
        .where(
            Generation.user_id == user.id,
            Generation.status.in_([GenerationStatus.QUEUED.value, GenerationStatus.PROCESSING.value]),
        )
        .order_by(Generation.created_at.desc())
    )
    generations = result.scalars().all()

    return {
        "generations": [
            {
                "id": g.id,
                "type": g.generation_type,
                "status": g.status,
                "credits_used": g.credits_used,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in generations
        ]
    }


@router.delete(
    "/{generation_id}",
    summary="Cancel a generation and refund credits",
    description="Cancel a queued generation and refund the credits to the user.",
    responses={
        200: {"description": "Generation cancelled and credits refunded"},
        400: {"description": "Generation cannot be cancelled (already processing or completed)"},
        401: {"description": "Authentication required"},
        404: {"description": "Generation not found"},
    },
)
async def cancel_generation(
    generation_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a queued generation and refund credits.

    Only generations in 'queued' status can be cancelled.
    """
    # Find the generation
    result = await db.execute(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.user_id == user.id,
        )
    )
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found",
        )

    # Check if it can be cancelled
    if generation.status != GenerationStatus.QUEUED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel generation with status '{generation.status}'. Only queued generations can be cancelled.",
        )

    # Refund credits
    credit_service = CreditService(db)
    await credit_service.refund_credits(
        user_id=user.id,
        amount=generation.credits_used,
        reason=f"Cancelled {generation.generation_type} generation",
        generation_id=generation.id,
    )

    # Update generation status
    generation.status = "cancelled"

    await db.commit()

    logger.info(f"Generation {generation_id} cancelled, {generation.credits_used} credits refunded to user {user.id}")

    return {
        "message": "Generation cancelled",
        "credits_refunded": generation.credits_used,
    }


@router.get(
    "/history",
    summary="Get generation history",
    description="Get the user's recent generation jobs.",
    responses={
        401: {"description": "Authentication required"},
    },
)
async def get_history(
    limit: int = Query(default=20, ge=1, le=100, description="Number of jobs to return"),
    offset: int = Query(default=0, ge=0, description="Number of jobs to skip"),
    user: User = Depends(require_auth),
):
    """
    Get the user's recent generation jobs from Redis cache.
    """
    queue = get_queue_service()
    jobs = await queue.get_user_jobs(user.id, limit=limit, offset=offset)

    return {
        "jobs": [
            JobResponse(
                id=job.id,
                status=job.status,
                progress=job.progress,
                result=job.result,
                error=job.error,
                type=job.type,
                created_at=job.created_at.isoformat(),
            )
            for job in jobs
        ],
        "total": len(jobs),
        "limit": limit,
        "offset": offset,
    }
