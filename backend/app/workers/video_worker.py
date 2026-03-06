"""Video processing worker using Celery.

This worker handles video post-processing including ping-pong effect
and re-uploads the processed video using the existing video_processor module.
"""

import logging
import shutil
import tempfile
from pathlib import Path

import requests
from celery import Task

from animation_creator.video_processor import VideoProcessor
from app.core.celery_config import celery_app
from app.core.database import create_worker_session_maker
from app.core.storage_config import get_storage_settings
from app.models.animation import Animation, AnimationStatus
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


def get_video_from_url(video_url: str, output_path: Path) -> None:
    """
    Download or copy video from URL to local path.

    Handles both remote HTTPS URLs and local storage URLs.
    For local storage, reads the file directly instead of via HTTP.

    Args:
        video_url: URL of the video (may be local or remote)
        output_path: Path to save the video to
    """
    storage_settings = get_storage_settings()

    # Check if it's a local storage URL
    if storage_settings.storage_mode == "local" and "/uploads/" in video_url:
        # Extract the file path from the URL
        relative_path = video_url.split("/uploads/", 1)[1]
        local_path = Path(storage_settings.local_storage_path) / relative_path

        if local_path.exists():
            # Copy file directly
            shutil.copy(local_path, output_path)
            logger.info(f"Copied local video file: {local_path}")
            return
        else:
            logger.warning(f"Local file not found: {local_path}, falling back to HTTP")

    # Fall back to HTTP download for remote URLs
    response = requests.get(video_url, timeout=120)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)


class VideoProcessingTask(Task):
    """Base task for video processing with error handling."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        animation_id = kwargs.get("animation_id")
        if animation_id:
            import asyncio
            asyncio.run(
                _mark_animation_failed(animation_id, str(exc))
            )
        logger.error(f"Video processing task {task_id} failed: {exc}")


@celery_app.task(
    bind=True,
    base=VideoProcessingTask,
    name="app.workers.video_worker.process_video",
    queue="video",
)
def process_video_task(
    self,
    animation_id: int,
    video_url: str,
    user_id: int,
    character_id: int,
) -> dict:
    """
    Process video with ping-pong effect.

    This creates a seamless loop by playing the video forward then backward.

    Args:
        animation_id: Animation database record ID.
        video_url: URL of the original video.
        user_id: User ID for storage path.
        character_id: Character ID for storage path.

    Returns:
        Dictionary with processed video URL.
    """
    import asyncio

    # Run all async operations in a single event loop to avoid connection pool issues
    return asyncio.run(
        _process_video_async(
            animation_id=animation_id,
            video_url=video_url,
            user_id=user_id,
            character_id=character_id,
        )
    )


async def _process_video_async(
    animation_id: int,
    video_url: str,
    user_id: int,
    character_id: int,
) -> dict:
    """Async implementation of video processing."""
    try:
        logger.info(f"Processing video for animation {animation_id}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.mp4"
            output_path = temp_path / "output.mp4"

            # Download or copy original video
            get_video_from_url(video_url, input_path)

            # Apply ping-pong effect
            VideoProcessor.make_ping_pong(input_path, output_path)

            # Upload processed video
            with open(output_path, "rb") as f:
                processed_bytes = f.read()

            storage = get_storage_service()
            processed_url = await storage.upload_file(
                file_bytes=processed_bytes,
                filename=f"animation_{animation_id}_pingpong.mp4",
                content_type="video/mp4",
                prefix=f"animations/{user_id}/{character_id}",
            )

            # Update animation record with processed video URL
            await _update_animation_video_url(animation_id, processed_url)

            # Queue GIF conversion with the processed video
            from app.workers.gif_worker import convert_to_gif_task
            convert_to_gif_task.delay(
                animation_id=animation_id,
                video_url=processed_url,
                user_id=user_id,
                character_id=character_id,
            )

            logger.info(f"Video processing complete for animation {animation_id}")
            return {
                "animation_id": animation_id,
                "video_url": processed_url,
            }

    except Exception as e:
        logger.error(f"Video processing failed for animation {animation_id}: {e}")
        await _mark_animation_failed(animation_id, str(e))
        raise


async def _update_animation_video_url(animation_id: int, video_url: str) -> None:
    """Update animation record with processed video URL."""
    session_maker = create_worker_session_maker()
    async with session_maker() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Animation).where(Animation.id == animation_id)
        )
        animation = result.scalar_one_or_none()
        if animation:
            animation.video_url = video_url
            await db.commit()


async def _mark_animation_failed(animation_id: int, error: str) -> None:
    """Mark animation record as failed."""
    session_maker = create_worker_session_maker()
    async with session_maker() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Animation).where(Animation.id == animation_id)
        )
        animation = result.scalar_one_or_none()
        if animation:
            animation.status = AnimationStatus.FAILED.value
            animation.error_message = error[:1000]
            await db.commit()
