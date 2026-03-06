"""Background worker processes.

This package contains Celery workers for generation tasks:
- character_worker: Character image generation
- animation_worker: Animation video generation
- video_worker: Video post-processing (ping-pong effect)
- gif_worker: GIF conversion with green screen removal
"""

from app.workers.animation_worker import generate_animation_task
from app.workers.character_worker import generate_character_task
from app.workers.gif_worker import convert_to_gif_task
from app.workers.video_worker import process_video_task

__all__ = [
    "generate_character_task",
    "generate_animation_task",
    "process_video_task",
    "convert_to_gif_task",
]
