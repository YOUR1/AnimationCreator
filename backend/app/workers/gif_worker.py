"""GIF conversion worker using Celery.

This worker handles converting animation videos to transparent GIFs
with green screen removal using the existing gif_converter module.
"""

import logging
import shutil
import tempfile
from pathlib import Path

import requests
from celery import Task

from animation_creator.config import Config
from animation_creator.gif_converter import GifConverter
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


class GifConversionTask(Task):
    """Base task for GIF conversion with error handling."""

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
        logger.error(f"GIF conversion task {task_id} failed: {exc}")


@celery_app.task(
    bind=True,
    base=GifConversionTask,
    name="app.workers.gif_worker.convert_to_gif",
    queue="gif",
)
def convert_to_gif_task(
    self,
    animation_id: int,
    video_url: str,
    user_id: int,
    character_id: int,
) -> dict:
    """
    Convert animation video to transparent GIF.

    This removes the green screen and creates a transparent GIF
    suitable for use as a game sprite or overlay.

    Args:
        animation_id: Animation database record ID.
        video_url: URL of the processed video.
        user_id: User ID for storage path.
        character_id: Character ID for storage path.

    Returns:
        Dictionary with GIF URL.
    """
    import asyncio

    # Run all async operations in a single event loop to avoid connection pool issues
    return asyncio.run(
        _convert_to_gif_async(
            animation_id=animation_id,
            video_url=video_url,
            user_id=user_id,
            character_id=character_id,
        )
    )


async def _convert_to_gif_async(
    animation_id: int,
    video_url: str,
    user_id: int,
    character_id: int,
) -> dict:
    """Async implementation of GIF conversion."""
    try:
        logger.info(f"Converting video to GIF for animation {animation_id}")

        # Initialize GIF converter
        config = Config()
        converter = GifConverter(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            video_path = temp_path / "input.mp4"
            gif_path = temp_path / "output.gif"

            # Download or copy video
            get_video_from_url(video_url, video_path)

            # Convert to transparent GIF with green screen removal
            # The ping-pong effect was already applied in video_worker
            converter.convert(
                video_path=video_path,
                output_path=gif_path,
                max_fps=config.GIF_FPS,
                edge_erode=2,
                ping_pong=False,  # Already ping-ponged
            )

            # Upload GIF to storage
            with open(gif_path, "rb") as f:
                gif_bytes = f.read()

            storage = get_storage_service()
            gif_url = await storage.upload_file(
                file_bytes=gif_bytes,
                filename=f"animation_{animation_id}.gif",
                content_type="image/gif",
                prefix=f"animations/{user_id}/{character_id}",
            )

            # Update animation record with GIF URL and mark as completed
            await _complete_animation(animation_id, gif_url)

            logger.info(f"GIF conversion complete for animation {animation_id}")
            return {
                "animation_id": animation_id,
                "gif_url": gif_url,
            }

    except Exception as e:
        logger.error(f"GIF conversion failed for animation {animation_id}: {e}")
        await _mark_animation_failed(animation_id, str(e))
        raise


async def _complete_animation(animation_id: int, gif_url: str) -> None:
    """Mark animation as completed with GIF URL."""
    session_maker = create_worker_session_maker()
    async with session_maker() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Animation).where(Animation.id == animation_id)
        )
        animation = result.scalar_one_or_none()
        if animation:
            animation.gif_url = gif_url
            animation.status = AnimationStatus.COMPLETED.value
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
