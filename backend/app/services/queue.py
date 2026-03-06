"""Job queue service for managing generation jobs.

This module provides a unified interface for creating, tracking, and managing
background generation jobs using Celery and Redis.
"""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import redis
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.animation import Animation, AnimationStatus
from app.models.character import Character
from app.models.generation import Generation, GenerationStatus

logger = logging.getLogger(__name__)
settings = get_settings()


class JobStatus(str, Enum):
    """Status of a generation job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Type of generation job."""

    CHARACTER = "character"
    ANIMATION = "animation"
    VIDEO = "video"
    GIF = "gif"


class Job(BaseModel):
    """Job model for tracking generation progress."""

    id: str = Field(description="Unique job identifier")
    user_id: int = Field(description="User who created the job")
    type: JobType = Field(description="Type of generation job")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage 0-100")
    result: Optional[dict[str, Any]] = Field(default=None, description="Job result on completion")
    error: Optional[str] = Field(default=None, description="Error message on failure")
    celery_task_id: Optional[str] = Field(default=None, description="Celery task ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Job-specific data
    character_id: Optional[int] = None
    animation_id: Optional[int] = None
    generation_id: Optional[int] = None

    class Config:
        use_enum_values = True


class JobQueueService:
    """Service for managing generation job queue with Redis."""

    JOB_PREFIX = "job:"
    JOB_TTL = 86400 * 7  # 7 days

    def __init__(self):
        """Initialize the job queue service."""
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    def _job_key(self, job_id: str) -> str:
        """Generate Redis key for a job."""
        return f"{self.JOB_PREFIX}{job_id}"

    def _user_jobs_key(self, user_id: int) -> str:
        """Generate Redis key for user's job list."""
        return f"user:{user_id}:jobs"

    async def create_job(
        self,
        user_id: int,
        job_type: JobType,
        character_id: Optional[int] = None,
        animation_id: Optional[int] = None,
        generation_id: Optional[int] = None,
    ) -> Job:
        """
        Create a new job entry in Redis.

        Args:
            user_id: The user creating the job.
            job_type: Type of generation job.
            character_id: Optional character reference.
            animation_id: Optional animation reference.
            generation_id: Optional generation record reference.

        Returns:
            Created Job object.
        """
        job_id = str(uuid.uuid4())

        job = Job(
            id=job_id,
            user_id=user_id,
            type=job_type,
            character_id=character_id,
            animation_id=animation_id,
            generation_id=generation_id,
        )

        # Store in Redis
        self.redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            job.model_dump_json(),
        )

        # Add to user's job list
        self.redis.lpush(self._user_jobs_key(user_id), job_id)
        self.redis.ltrim(self._user_jobs_key(user_id), 0, 99)  # Keep last 100 jobs

        logger.info(f"Created job {job_id} of type {job_type} for user {user_id}")
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by its ID.

        Args:
            job_id: The job identifier.

        Returns:
            Job object if found, None otherwise.
        """
        data = self.redis.get(self._job_key(job_id))
        if data:
            return Job.model_validate_json(data)
        return None

    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        celery_task_id: Optional[str] = None,
    ) -> Optional[Job]:
        """
        Update a job's status and progress.

        Args:
            job_id: The job identifier.
            status: New job status.
            progress: New progress percentage.
            result: Job result data.
            error: Error message.
            celery_task_id: Celery task ID reference.

        Returns:
            Updated Job object if found, None otherwise.
        """
        job = await self.get_job(job_id)
        if not job:
            return None

        now = datetime.utcnow()

        if status is not None:
            job.status = status
            if status == JobStatus.PROCESSING and job.started_at is None:
                job.started_at = now
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                job.completed_at = now

        if progress is not None:
            job.progress = min(100, max(0, progress))

        if result is not None:
            job.result = result

        if error is not None:
            job.error = error

        if celery_task_id is not None:
            job.celery_task_id = celery_task_id

        # Save updated job
        self.redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            job.model_dump_json(),
        )

        logger.info(f"Updated job {job_id}: status={status}, progress={progress}")
        return job

    async def get_user_jobs(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Job]:
        """
        Get jobs for a specific user.

        Args:
            user_id: The user ID.
            limit: Maximum number of jobs to return.
            offset: Number of jobs to skip.

        Returns:
            List of Job objects.
        """
        job_ids = self.redis.lrange(
            self._user_jobs_key(user_id),
            offset,
            offset + limit - 1,
        )

        jobs = []
        for job_id in job_ids:
            job = await self.get_job(job_id)
            if job:
                jobs.append(job)

        return jobs

    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from Redis.

        Args:
            job_id: The job identifier.

        Returns:
            True if deleted, False if not found.
        """
        result = self.redis.delete(self._job_key(job_id))
        return result > 0

    def publish_progress(self, job_id: str, progress: int, message: str = "") -> None:
        """
        Publish progress update to Redis pub/sub for SSE streaming.

        Args:
            job_id: The job identifier.
            progress: Progress percentage.
            message: Optional progress message.
        """
        channel = f"job:{job_id}:progress"
        data = json.dumps({
            "job_id": job_id,
            "progress": progress,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.redis.publish(channel, data)


# Global instance
_queue_service: Optional[JobQueueService] = None


def get_queue_service() -> JobQueueService:
    """Get or create queue service instance."""
    global _queue_service
    if _queue_service is None:
        _queue_service = JobQueueService()
    return _queue_service


# Convenience functions for the interface contract


async def create_character_job(
    db: AsyncSession,
    user_id: int,
    name: str,
    prompt: str,
    style: str,
    generation_id: int,
) -> Job:
    """
    Create a character generation job.

    Args:
        db: Database session.
        user_id: User ID.
        name: Character name.
        prompt: Character description prompt.
        style: Style preset key.
        generation_id: Generation record ID.

    Returns:
        Created Job object.
    """
    from app.workers.character_worker import generate_character_task

    service = get_queue_service()

    # Create job entry
    job = await service.create_job(
        user_id=user_id,
        job_type=JobType.CHARACTER,
        generation_id=generation_id,
    )

    # Queue Celery task
    task = generate_character_task.delay(
        job_id=job.id,
        user_id=user_id,
        name=name,
        prompt=prompt,
        style=style,
        generation_id=generation_id,
    )

    # Update job with Celery task ID
    await service.update_job(job.id, celery_task_id=task.id)

    logger.info(f"Created character generation job {job.id} with task {task.id}")
    return job


async def create_animation_job(
    db: AsyncSession,
    user_id: int,
    character_id: int,
    states: list[str],
    generation_id: int,
    custom_prompt: str | None = None,
    duration: int = 5,
    aspect_ratio: str = "1:1",
    negative_prompt: str | None = None,
    cfg_scale: float | None = None,
    special_fx: str | None = None,
    seamless_loop: bool = False,
) -> Job:
    """
    Create an animation generation job.

    Args:
        db: Database session.
        user_id: User ID.
        character_id: Character to animate.
        states: List of animation state keys.
        generation_id: Generation record ID.
        custom_prompt: Custom animation description/prompt.
        duration: Animation duration in seconds (5 or 10).
        aspect_ratio: Output aspect ratio (1:1, 16:9, 9:16).
        negative_prompt: Elements to avoid in generation.
        cfg_scale: Classifier Free Guidance scale.
        special_fx: Special effects (hug, kiss, heart_gesture, squish, expansion).
        seamless_loop: Whether to create a seamless loop using ping-pong effect.

    Returns:
        Created Job object.
    """
    from app.workers.animation_worker import generate_animation_task

    service = get_queue_service()

    # Get character for validation
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == user_id,
        )
    )
    character = result.scalar_one_or_none()

    if not character:
        raise ValueError(f"Character {character_id} not found for user {user_id}")

    if not character.image_url:
        raise ValueError(f"Character {character_id} has no image")

    # Create job entry
    job = await service.create_job(
        user_id=user_id,
        job_type=JobType.ANIMATION,
        character_id=character_id,
        generation_id=generation_id,
    )

    # Queue Celery task with all parameters
    task = generate_animation_task.delay(
        job_id=job.id,
        user_id=user_id,
        character_id=character_id,
        character_prompt=character.prompt,
        character_image_url=character.image_url,
        states=states,
        generation_id=generation_id,
        custom_prompt=custom_prompt,
        duration=duration,
        aspect_ratio=aspect_ratio,
        negative_prompt=negative_prompt,
        cfg_scale=cfg_scale,
        special_fx=special_fx,
        seamless_loop=seamless_loop,
    )

    # Update job with Celery task ID
    await service.update_job(job.id, celery_task_id=task.id)

    logger.info(f"Created animation generation job {job.id} with task {task.id}")
    return job


async def get_job_status(job_id: str) -> Optional[Job]:
    """
    Get the status of a job.

    Args:
        job_id: Job identifier.

    Returns:
        Job object if found, None otherwise.
    """
    service = get_queue_service()
    return await service.get_job(job_id)


async def sync_job_with_database(
    db: AsyncSession,
    job: Job,
) -> None:
    """
    Synchronize job status with database records.

    This updates the Generation, Character, or Animation records
    based on the job's current status.

    Args:
        db: Database session.
        job: Job to synchronize.
    """
    if job.generation_id:
        result = await db.execute(
            select(Generation).where(Generation.id == job.generation_id)
        )
        generation = result.scalar_one_or_none()

        if generation:
            if job.status == JobStatus.PROCESSING:
                generation.mark_started()
            elif job.status == JobStatus.COMPLETED:
                generation.mark_completed()
            elif job.status == JobStatus.FAILED:
                generation.mark_failed(job.error or "Unknown error")

            await db.flush()
