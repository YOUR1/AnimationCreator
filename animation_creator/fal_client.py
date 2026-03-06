"""fal.ai API client wrapper."""

import os
import time
import fal_client
import requests
from pathlib import Path

from .config import Config


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
        # Build arguments dict with required params
        arguments = {
            "prompt": prompt,
            "image_url": image_url,
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

        result = fal_client.subscribe(
            self.config.KLING_MODEL,
            arguments=arguments,
            with_logs=False,
        )

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
