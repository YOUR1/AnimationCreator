"""Animation generation worker using Celery.

This worker handles animation generation using the fal.ai Kling model
through the existing animation_creator module.
"""

import base64
import logging
import mimetypes
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from celery import Task

from animation_creator.animator import Animator
from animation_creator.config import Config
from animation_creator.fal_client import FalClient
from app.core.celery_config import celery_app
from app.core.database import create_worker_session_maker
from app.core.storage_config import get_storage_settings
from app.models.animation import Animation, AnimationStatus
from app.models.generation import Generation
from app.services.queue import JobQueueService, JobStatus, get_queue_service
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


def convert_local_url_to_data_uri(image_url: str) -> str:
    """
    Convert a local storage URL to a base64 data URI.

    fal.ai requires either HTTPS URLs or data URIs. In development mode,
    we use local storage with localhost URLs which aren't accessible from
    fal.ai servers. This function converts those to data URIs.

    Args:
        image_url: The image URL (may be local or remote)

    Returns:
        Either the original URL (if HTTPS) or a data URI (if local)
    """
    parsed = urlparse(image_url)

    # If it's already HTTPS, return as-is
    if parsed.scheme == "https":
        return image_url

    # Check if it's a local URL (localhost or local storage path)
    storage_settings = get_storage_settings()

    if storage_settings.storage_mode != "local":
        # Not using local storage, return URL as-is
        return image_url

    # Extract the file path from the URL
    # URL format: http://localhost:3131/uploads/characters/1/2026/03/05/filename.png
    # We need to extract: characters/1/2026/03/05/filename.png
    if "/uploads/" in image_url:
        relative_path = image_url.split("/uploads/", 1)[1]
        local_path = Path(storage_settings.local_storage_path) / relative_path

        if local_path.exists():
            # Read file and convert to base64
            mime_type = mimetypes.guess_type(str(local_path))[0] or "image/png"

            with open(local_path, "rb") as f:
                image_data = f.read()

            base64_data = base64.b64encode(image_data).decode("utf-8")
            data_uri = f"data:{mime_type};base64,{base64_data}"

            logger.info(f"Converted local URL to data URI: {image_url[:50]}...")
            return data_uri
        else:
            logger.warning(f"Local file not found: {local_path}")

    # Fallback: return original URL
    return image_url


class AnimationGenerationTask(Task):
    """Base task for animation generation with error handling."""

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
            queue.redis.setex(
                f"job:{job_id}:error",
                86400,
                str(exc),
            )
        logger.error(f"Animation generation task {task_id} failed: {exc}")


@celery_app.task(
    bind=True,
    base=AnimationGenerationTask,
    name="app.workers.animation_worker.generate_animation",
    queue="animation",
)
def generate_animation_task(
    self,
    job_id: str,
    user_id: int,
    character_id: int,
    character_prompt: str,
    character_image_url: str,
    states: list[str],
    generation_id: int,
    custom_prompt: str | None = None,
    duration: int = 5,
    aspect_ratio: str = "1:1",
    negative_prompt: str | None = None,
    cfg_scale: float | None = None,
    special_fx: str | None = None,
    seamless_loop: bool = False,
) -> dict:
    """
    Generate animations for a character.

    Args:
        job_id: Job queue ID for progress tracking.
        user_id: User ID who requested the generation.
        character_id: Character ID to animate.
        character_prompt: Original character description.
        character_image_url: URL of the character image.
        states: List of animation state keys (idle, walk, run, jump, attack, etc.).
        generation_id: Database generation record ID.
        custom_prompt: Custom animation description/prompt.
        duration: Animation duration in seconds (5 or 10).
        aspect_ratio: Output aspect ratio (1:1, 16:9, 9:16).
        negative_prompt: Elements to avoid in generation.
        cfg_scale: Classifier Free Guidance scale.
        special_fx: Special effects (hug, kiss, heart_gesture, squish, expansion).
        seamless_loop: Whether to create a seamless loop using ping-pong effect.

    Returns:
        Dictionary with animation results.
    """
    import asyncio

    # Run all async operations in a single event loop to avoid connection pool issues
    return asyncio.run(
        _generate_animation_async(
            job_id=job_id,
            user_id=user_id,
            character_id=character_id,
            character_prompt=character_prompt,
            character_image_url=character_image_url,
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
    )


async def _generate_animation_async(
    job_id: str,
    user_id: int,
    character_id: int,
    character_prompt: str,
    character_image_url: str,
    states: list[str],
    generation_id: int,
    custom_prompt: str | None = None,
    duration: int = 5,
    aspect_ratio: str = "1:1",
    negative_prompt: str | None = None,
    cfg_scale: float | None = None,
    special_fx: str | None = None,
    seamless_loop: bool = False,
) -> dict:
    """Async implementation of animation generation."""
    queue = get_queue_service()
    total_states = len(states)
    animations_created = []

    try:
        # Update job status to processing
        await queue.update_job(job_id, status=JobStatus.PROCESSING, progress=5)
        queue.publish_progress(job_id, 5, "Starting animation generation...")

        # Update generation record status to processing
        await _mark_generation_processing(generation_id)

        # Initialize fal.ai client
        config = Config()
        fal_client = FalClient(config)
        animator = Animator(fal_client, config)

        # Convert local URL to data URI for fal.ai compatibility
        image_url_for_fal = convert_local_url_to_data_uri(character_image_url)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            storage = get_storage_service()

            for idx, state in enumerate(states):
                state_progress_base = 10 + (idx * 80 // total_states)
                state_name = config.ANIMATION_STATES.get(state, {}).get("name", state)

                queue.publish_progress(
                    job_id,
                    state_progress_base,
                    f"Generating {state_name} animation ({idx + 1}/{total_states})..."
                )
                await queue.update_job(job_id, progress=state_progress_base)

                # Generate animation with all parameters (sync call)
                output_path = output_dir / f"{state}.mp4"
                animator.animate(
                    image_url=image_url_for_fal,
                    character_description=character_prompt,
                    animation_state=state,
                    output_path=output_path,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    custom_prompt=custom_prompt,
                    negative_prompt=negative_prompt,
                    cfg_scale=cfg_scale,
                    special_fx=special_fx,
                )

                # Upload video to storage
                upload_progress = state_progress_base + (40 // total_states)
                queue.publish_progress(
                    job_id,
                    upload_progress,
                    f"Uploading {state_name} animation..."
                )

                with open(output_path, "rb") as f:
                    video_bytes = f.read()

                video_url = await storage.upload_file(
                    file_bytes=video_bytes,
                    filename=f"{state}_{job_id}.mp4",
                    content_type="video/mp4",
                    prefix=f"animations/{user_id}/{character_id}",
                )

                # Create animation record in database
                animation_id = await _create_animation_record(
                    character_id=character_id,
                    state=state,
                    video_url=video_url,
                    generation_id=generation_id,
                )

                animations_created.append({
                    "animation_id": animation_id,
                    "state": state,
                    "video_url": video_url,
                })

                # Queue video processing (ping-pong if enabled) and GIF conversion
                from app.workers.video_worker import process_video_task

                process_video_task.delay(
                    animation_id=animation_id,
                    video_url=video_url,
                    user_id=user_id,
                    character_id=character_id,
                    seamless_loop=seamless_loop,
                )

        # Update job as completed
        result = {
            "character_id": character_id,
            "animations": animations_created,
        }

        await queue.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=result,
        )
        queue.publish_progress(job_id, 100, "Animation generation complete!")

        # Update generation record
        await _mark_generation_completed(generation_id)

        logger.info(
            f"Animation generation complete: job={job_id}, "
            f"character={character_id}, animations={len(animations_created)}"
        )
        return result

    except Exception as e:
        logger.error(f"Animation generation failed: {e}")

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


async def _create_animation_record(
    character_id: int,
    state: str,
    video_url: str,
    generation_id: int,
) -> int:
    """
    Create animation record in database.

    Args:
        character_id: Character ID.
        state: Animation state.
        video_url: URL of generated video.
        generation_id: Generation record ID.

    Returns:
        Animation ID.
    """
    session_maker = create_worker_session_maker()
    async with session_maker() as db:
        animation = Animation(
            character_id=character_id,
            state=state,
            video_url=video_url,
            status=AnimationStatus.PROCESSING.value,  # Still processing (ping-pong, GIF)
            generation_id=generation_id,
        )
        db.add(animation)
        await db.commit()
        return animation.id


async def _mark_generation_processing(generation_id: int) -> None:
    """Mark generation record as processing."""
    session_maker = create_worker_session_maker()
    async with session_maker() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        generation = result.scalar_one_or_none()
        if generation:
            generation.mark_started()
            await db.commit()


async def _mark_generation_completed(generation_id: int) -> None:
    """Mark generation record as completed."""
    session_maker = create_worker_session_maker()
    async with session_maker() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        generation = result.scalar_one_or_none()
        if generation:
            generation.mark_completed()
            await db.commit()


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
