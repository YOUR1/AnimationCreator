"""Celery configuration for background task processing.

This module configures Celery for the generation engine, handling
character generation, animation processing, and video/GIF conversion.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.

    Returns:
        Configured Celery application instance.
    """
    celery_app = Celery(
        "animation_creator",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )

    # Celery configuration
    celery_app.conf.update(
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,

        # Result backend settings
        result_expires=86400,  # 24 hours
        result_extended=True,  # Store additional metadata

        # Task execution settings
        task_acks_late=True,  # Acknowledge after completion
        task_reject_on_worker_lost=True,  # Reject on worker crash

        # Retry settings
        task_default_retry_delay=60,  # 1 minute
        task_max_retries=3,

        # Task routing
        task_routes={
            "app.workers.character_worker.*": {"queue": "character"},
            "app.workers.animation_worker.*": {"queue": "animation"},
            "app.workers.video_worker.*": {"queue": "video"},
            "app.workers.gif_worker.*": {"queue": "gif"},
        },

        # Worker settings
        worker_prefetch_multiplier=1,  # Process one task at a time
        worker_concurrency=settings.celery_worker_concurrency,  # Configurable via env

        # Task time limits
        task_soft_time_limit=600,  # 10 minutes soft limit
        task_time_limit=660,  # 11 minutes hard limit

        # Imports
        imports=[
            "app.workers.character_worker",
            "app.workers.animation_worker",
            "app.workers.video_worker",
            "app.workers.gif_worker",
        ],
    )

    return celery_app


# Global Celery app instance
celery_app = create_celery_app()


# Celery startup command helper
def get_worker_command(queue: str | None = None) -> list[str]:
    """
    Get the command to start a Celery worker.

    Args:
        queue: Optional specific queue to process.
               If None, processes all queues.

    Returns:
        List of command arguments.
    """
    cmd = [
        "celery",
        "-A",
        "app.core.celery_config",
        "worker",
        "--loglevel=info",
    ]

    if queue:
        cmd.extend(["-Q", queue])
    else:
        cmd.extend(["-Q", "character,animation,video,gif"])

    return cmd
