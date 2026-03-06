"""Character generation worker using Celery.

This worker handles character image generation using the fal.ai FLUX model
through the existing animation_creator module.
"""

import logging
import tempfile
from pathlib import Path

from celery import Task

from animation_creator.character_generator import CharacterGenerator
from animation_creator.config import Config
from animation_creator.fal_client import FalClient
from app.core.celery_config import celery_app
from app.core.database import create_worker_session_maker
from app.models.character import Character
from app.models.generation import Generation, GenerationStatus
from app.services.queue import JobQueueService, JobStatus, get_queue_service
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


class CharacterGenerationTask(Task):
    """Base task for character generation with error handling."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        job_id = kwargs.get("job_id")
        if job_id:
            queue = get_queue_service()
            # Use sync redis operations in callback
            queue.redis.setex(
                f"job:{job_id}:error",
                86400,
                str(exc),
            )
        logger.error(f"Character generation task {task_id} failed: {exc}")


@celery_app.task(
    bind=True,
    base=CharacterGenerationTask,
    name="app.workers.character_worker.generate_character",
    queue="character",
)
def generate_character_task(
    self,
    job_id: str,
    user_id: int,
    name: str,
    prompt: str,
    style: str,
    generation_id: int,
) -> dict:
    """
    Generate a character image.

    Args:
        job_id: Job queue ID for progress tracking.
        user_id: User ID who requested the generation.
        name: Character name.
        prompt: Character description prompt.
        style: Style preset key (kawaii, pixar, realistic, pixel, watercolor).
        generation_id: Database generation record ID.

    Returns:
        Dictionary with character_id and image_url.
    """
    import asyncio

    # Run all async operations in a single event loop to avoid connection pool issues
    return asyncio.run(
        _generate_character_async(
            job_id=job_id,
            user_id=user_id,
            name=name,
            prompt=prompt,
            style=style,
            generation_id=generation_id,
        )
    )


async def _generate_character_async(
    job_id: str,
    user_id: int,
    name: str,
    prompt: str,
    style: str,
    generation_id: int,
) -> dict:
    """Async implementation of character generation."""
    queue = get_queue_service()

    try:
        # Update job status to processing
        await queue.update_job(job_id, status=JobStatus.PROCESSING, progress=5)
        queue.publish_progress(job_id, 5, "Starting character generation...")

        # Initialize fal.ai client
        config = Config()
        fal_client = FalClient(config)
        generator = CharacterGenerator(fal_client, config)

        queue.publish_progress(job_id, 10, "Generating character image...")
        await queue.update_job(job_id, progress=10)

        # Generate character in temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "character.png"

            # Generate the character image (sync call)
            generator.generate(
                character_description=prompt,
                style_key=style,
                output_path=output_path,
            )

            queue.publish_progress(job_id, 60, "Uploading character image...")
            await queue.update_job(job_id, progress=60)

            # Read generated image
            with open(output_path, "rb") as f:
                image_bytes = f.read()

            # Upload to storage
            storage = get_storage_service()
            image_url = await storage.upload_file(
                file_bytes=image_bytes,
                filename=f"character_{job_id}.png",
                content_type="image/png",
                prefix=f"characters/{user_id}",
            )

        queue.publish_progress(job_id, 80, "Saving character to database...")
        await queue.update_job(job_id, progress=80)

        # Save character to database
        character_id = await _save_character_to_db(
            user_id=user_id,
            name=name,
            prompt=prompt,
            style=style,
            image_url=image_url,
            generation_id=generation_id,
        )

        # Update job as completed
        result = {
            "character_id": character_id,
            "image_url": image_url,
        }

        await queue.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=result,
        )
        queue.publish_progress(job_id, 100, "Character generation complete!")

        logger.info(f"Character generation complete: job={job_id}, character={character_id}")
        return result

    except Exception as e:
        logger.error(f"Character generation failed: {e}")

        # Update job as failed
        await queue.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(e),
        )
        queue.publish_progress(job_id, 0, f"Generation failed: {str(e)}")

        # Update generation record as failed
        await _mark_generation_failed(generation_id, str(e))

        raise


async def _save_character_to_db(
    user_id: int,
    name: str,
    prompt: str,
    style: str,
    image_url: str,
    generation_id: int,
) -> int:
    """
    Save generated character to database.

    Args:
        user_id: User ID.
        name: Character name.
        prompt: Character prompt.
        style: Style used.
        image_url: URL of generated image.
        generation_id: Generation record ID.

    Returns:
        Character ID.
    """
    session_maker = create_worker_session_maker()
    async with session_maker() as db:
        # Create character record
        character = Character(
            user_id=user_id,
            name=name,
            prompt=prompt,
            style=style,
            image_url=image_url,
        )
        db.add(character)

        # Update generation record
        from sqlalchemy import select
        result = await db.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        generation = result.scalar_one_or_none()
        if generation:
            generation.mark_completed()

        await db.commit()

        return character.id


async def _mark_generation_failed(generation_id: int, error: str) -> None:
    """Mark generation record as failed."""
    session_maker = create_worker_session_maker()
    async with session_maker() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        generation = result.scalar_one_or_none()
        if generation:
            generation.mark_failed(error)
            await db.commit()
