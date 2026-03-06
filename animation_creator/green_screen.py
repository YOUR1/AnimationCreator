"""Green screen background processing."""

from pathlib import Path
import numpy as np
from PIL import Image

from .config import Config


class GreenScreenProcessor:
    """Processes images to add green screen background."""

    def __init__(self, config: Config):
        """Initialize the green screen processor."""
        self.config = config
        self.green_color = config.GREEN_SCREEN_COLOR
        self._rembg_session = None

    def remove_background(
        self,
        image: Image.Image,
        alpha_matting: bool = True,
        alpha_matting_foreground_threshold: int = 240,
        alpha_matting_background_threshold: int = 10,
    ) -> Image.Image:
        """
        Remove the background from an image.

        Args:
            image: PIL Image with background to remove
            alpha_matting: Use alpha matting for better edge quality
            alpha_matting_foreground_threshold: Threshold for foreground (higher = more conservative)
            alpha_matting_background_threshold: Threshold for background

        Returns:
            PIL Image with transparent background (RGBA)
        """
        from rembg import remove, new_session

        # Use a session for better performance on multiple calls
        if self._rembg_session is None:
            self._rembg_session = new_session("u2net")

        return remove(
            image,
            session=self._rembg_session,
            alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
        )

    def add_green_background(
        self,
        image: Image.Image,
        padding_percent: float = 0.15,
    ) -> Image.Image:
        """
        Add green screen background to a transparent image.

        Args:
            image: PIL Image with transparent background (RGBA)
            padding_percent: Padding around character as percentage of image size

        Returns:
            PIL Image with green background
        """
        # Ensure image has alpha channel
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Get the bounding box of non-transparent content
        bbox = image.getbbox()
        if bbox is None:
            # Image is fully transparent, return green canvas
            green_bg = Image.new("RGB", image.size, self.green_color)
            return green_bg

        # Crop to content
        cropped = image.crop(bbox)

        # Calculate new canvas size with padding
        content_width, content_height = cropped.size
        padding_x = int(content_width * padding_percent)
        padding_y = int(content_height * padding_percent)

        new_width = content_width + (padding_x * 2)
        new_height = content_height + (padding_y * 2)

        # Create green background canvas
        green_bg = Image.new("RGB", (new_width, new_height), self.green_color)

        # Calculate position to center the character
        x = padding_x
        y = padding_y

        # Paste character onto green background using alpha as mask
        green_bg.paste(cropped, (x, y), cropped)

        return green_bg

    def process(
        self,
        input_path: Path,
        output_path: Path,
        target_size: tuple[int, int] | None = None,
    ) -> Path:
        """
        Process an image: remove background and add green screen.

        Args:
            input_path: Path to input image
            output_path: Path to save processed image
            target_size: Optional (width, height) to resize to

        Returns:
            Path to the saved image
        """
        # Load image
        image = Image.open(input_path)

        # Remove background
        transparent = self.remove_background(image)

        # Add green background
        green_screen = self.add_green_background(transparent)

        # Resize if target size specified
        if target_size:
            green_screen = green_screen.resize(target_size, Image.Resampling.LANCZOS)

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        green_screen.save(output_path, "PNG")

        return output_path

    def normalize_green_background(
        self,
        image: Image.Image,
        tolerance: int = 50,
    ) -> Image.Image:
        """
        Replace the background color with pure chroma key green (#00FF00).

        Samples the background color from the top-left corner only,
        then replaces pixels matching that exact color. This preserves
        any green parts of the character that are a different shade.

        Args:
            image: PIL Image with solid color background
            tolerance: Color distance tolerance (lower = more precise)

        Returns:
            PIL Image with pure green background
        """
        img_array = np.array(image.convert("RGB"))

        # Sample background color from top-left 20x20 pixels only
        sample_size = 20
        top_left = img_array[:sample_size, :sample_size]
        bg_color = top_left.mean(axis=(0, 1))

        # Calculate color distance from the sampled background color
        diff = np.sqrt(np.sum((img_array.astype(float) - bg_color) ** 2, axis=2))

        # Create mask: True for pixels matching the background color
        bg_mask = diff < tolerance

        # Replace background with pure green
        result = img_array.copy()
        result[bg_mask] = self.green_color

        return Image.fromarray(result)

    def normalize_green_file(
        self,
        input_path: Path,
        output_path: Path | None = None,
        tolerance: int = 80,
    ) -> Path:
        """
        Normalize green background of an image file.

        Args:
            input_path: Path to input image
            output_path: Path to save (defaults to overwriting input)
            tolerance: Color distance tolerance

        Returns:
            Path to the saved image
        """
        if output_path is None:
            output_path = input_path

        image = Image.open(input_path)
        normalized = self.normalize_green_background(image, tolerance)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(output_path, "PNG")

        return output_path

    def upload_for_video(self, image_path: Path) -> str:
        """
        Upload a local image to fal.ai storage for video generation.

        Args:
            image_path: Path to the local image file

        Returns:
            URL of the uploaded image
        """
        import fal_client

        url = fal_client.upload_file(str(image_path))
        return url
