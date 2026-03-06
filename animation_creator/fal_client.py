"""fal.ai API client wrapper."""

import base64
import io
import logging
import os
import time
import fal_client
import requests
from pathlib import Path
from PIL import Image

from .config import Config

logger = logging.getLogger(__name__)


def pad_image_to_aspect_ratio(
    image_data: bytes,
    target_aspect_ratio: str,
    background_color: tuple[int, int, int] = (0, 177, 64),  # Green screen color
) -> str:
    """
    Pad an image to match the target aspect ratio, aligning content to the bottom.

    Args:
        image_data: Raw image bytes
        target_aspect_ratio: Target ratio as string (e.g., "9:16", "16:9", "1:1")
        background_color: RGB color for padding (default: green screen)

    Returns:
        Base64 data URI of the padded image
    """
    # Parse aspect ratio
    ratio_map = {
        "1:1": (1, 1),
        "16:9": (16, 9),
        "9:16": (9, 16),
    }

    if target_aspect_ratio not in ratio_map:
        logger.warning(f"Unknown aspect ratio {target_aspect_ratio}, using 1:1")
        target_aspect_ratio = "1:1"

    target_w_ratio, target_h_ratio = ratio_map[target_aspect_ratio]

    # Load image
    img = Image.open(io.BytesIO(image_data))
    original_width, original_height = img.size
    original_ratio = original_width / original_height
    target_ratio = target_w_ratio / target_h_ratio

    logger.info(f"Original image: {original_width}x{original_height} (ratio: {original_ratio:.2f})")
    logger.info(f"Target aspect ratio: {target_aspect_ratio} (ratio: {target_ratio:.2f})")

    # If already matching, return as-is
    if abs(original_ratio - target_ratio) < 0.01:
        logger.info("Image already matches target aspect ratio")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{base64_data}"

    # Calculate new dimensions
    if target_ratio > original_ratio:
        # Target is wider - add padding to sides (center horizontally)
        new_height = original_height
        new_width = int(original_height * target_ratio)
        paste_x = (new_width - original_width) // 2
        paste_y = 0
    else:
        # Target is taller - add padding to top (align to bottom)
        new_width = original_width
        new_height = int(original_width / target_ratio)
        paste_x = 0
        paste_y = new_height - original_height  # Align to bottom

    logger.info(f"New canvas: {new_width}x{new_height}, pasting at ({paste_x}, {paste_y})")

    # Create new image with background color
    if img.mode == "RGBA":
        new_img = Image.new("RGBA", (new_width, new_height), (*background_color, 255))
    else:
        new_img = Image.new("RGB", (new_width, new_height), background_color)

    # Paste original image (aligned to bottom for taller targets)
    new_img.paste(img, (paste_x, paste_y))

    # Convert to base64 data URI
    buffer = io.BytesIO()
    new_img.save(buffer, format="PNG")
    base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{base64_data}"


class FalClient:
    """Wrapper for fal.ai API interactions."""

    def __init__(self, config: Config):
        """Initialize the fal.ai client."""
        self.config = config
        os.environ["FAL_KEY"] = config.fal_key

    def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
    ) -> list[str]:
        """
        Generate images using FLUX model.

        Args:
            prompt: Text description of the image to generate
            width: Image width in pixels
            height: Image height in pixels
            num_images: Number of images to generate

        Returns:
            List of image URLs
        """
        result = fal_client.subscribe(
            self.config.FLUX_MODEL,
            arguments={
                "prompt": prompt,
                "image_size": {
                    "width": width,
                    "height": height,
                },
                "num_images": num_images,
                "safety_tolerance": "2",
            },
            with_logs=False,
        )

        return [img["url"] for img in result["images"]]

    def generate_video(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "1:1",
        negative_prompt: str | None = None,
        cfg_scale: float | None = None,
        static_mask_url: str | None = None,
        dynamic_mask_url: str | None = None,
        special_fx: str | None = None,
    ) -> str:
        """
        Generate video from image using Kling model.

        Args:
            image_url: URL of the source image
            prompt: Animation prompt describing the motion
            duration: Video duration in seconds (5 or 10)
            aspect_ratio: Video aspect ratio (16:9, 9:16, or 1:1)
            negative_prompt: Elements to avoid in the generation
            cfg_scale: Classifier Free Guidance scale (default: 0.5)
            static_mask_url: URL for static motion brush mask
            dynamic_mask_url: URL for dynamic motion brush mask
            special_fx: Special effects (hug, kiss, heart_gesture, squish, expansion)

        Returns:
            URL of the generated video
        """
        # Preprocess image to match target aspect ratio
        # fal.ai Kling image-to-video uses input image dimensions, so we need to pad
        processed_image_url = image_url
        if aspect_ratio != "1:1":
            try:
                logger.info(f"Preprocessing image for aspect ratio {aspect_ratio}")
                response = requests.get(image_url, timeout=60)
                response.raise_for_status()
                processed_image_url = pad_image_to_aspect_ratio(
                    response.content,
                    aspect_ratio,
                )
                logger.info("Image preprocessed successfully")
            except Exception as e:
                logger.warning(f"Failed to preprocess image, using original: {e}")

        # Build arguments dict with required params
        arguments = {
            "prompt": prompt,
            "image_url": processed_image_url,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
        }

        # Add optional parameters if provided
        if negative_prompt:
            arguments["negative_prompt"] = negative_prompt
        if cfg_scale is not None:
            arguments["cfg_scale"] = cfg_scale
        if static_mask_url:
            arguments["static_mask_url"] = static_mask_url
        if dynamic_mask_url:
            arguments["dynamic_mask_url"] = dynamic_mask_url
        if special_fx:
            arguments["special_fx"] = special_fx

        # Don't log the full base64 data URI
        log_args = {k: (v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v) for k, v in arguments.items()}
        logger.info(f"Calling fal.ai Kling model with arguments: {log_args}")

        result = fal_client.subscribe(
            self.config.KLING_MODEL,
            arguments=arguments,
            with_logs=False,
        )

        logger.info(f"fal.ai response video URL: {result['video']['url']}")
        return result["video"]["url"]

    @staticmethod
    def download_file(url: str, output_path: Path, max_retries: int = 3) -> Path:
        """
        Download a file from URL to local path.

        Args:
            url: URL to download from
            output_path: Local path to save the file
            max_retries: Maximum number of retry attempts

        Returns:
            Path to the downloaded file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        for attempt in range(max_retries):
            try:
                response = requests.get(url, stream=True, timeout=60)
                response.raise_for_status()

                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                return output_path

            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to download {url}: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

        return output_path
