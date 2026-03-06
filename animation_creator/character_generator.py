"""Character image generation using fal.ai FLUX."""

from pathlib import Path

from .config import Config
from .fal_client import FalClient


class CharacterGenerator:
    """Generates character designs using fal.ai FLUX model."""

    def __init__(self, fal_client: FalClient, config: Config):
        """Initialize the character generator."""
        self.fal_client = fal_client
        self.config = config

    def build_prompt(
        self,
        character_description: str,
        style_key: str,
        green_screen: bool = True,
    ) -> str:
        """
        Build a complete prompt for character generation.

        Args:
            character_description: User's description of the character
            style_key: Key of the style preset to use
            green_screen: If True, generate on green screen background

        Returns:
            Complete prompt string
        """
        style_prompt = self.config.get_style_prompt(style_key)

        if green_screen:
            background = (
                "solid bright green background #00FF00, chroma key green screen, "
                "character floating in center"
            )
            lighting = (
                "flat even studio lighting, soft diffused light, shadowless, "
                "front-lit, uniform illumination"
            )
        else:
            background = "clean simple background"
            lighting = "soft even lighting"

        # Build prompt optimized for character generation
        # Lighting comes early for priority, negatives avoided
        prompt = (
            f"{lighting}, {character_description}, {style_prompt}, "
            f"single character, centered composition, full body visible, "
            f"{background}, character design, mascot style, "
            "high quality, detailed, 2D flat illustration"
        )

        return prompt

    def generate(
        self,
        character_description: str,
        style_key: str,
        output_path: Path,
        size: int = 1024,
    ) -> Path:
        """
        Generate a character image.

        Args:
            character_description: Description of the character to create
            style_key: Style preset key (kawaii, pixar, realistic, pixel, watercolor)
            output_path: Path to save the generated image
            size: Image size in pixels (square)

        Returns:
            Path to the saved character image
        """
        prompt = self.build_prompt(character_description, style_key)

        # Generate image
        image_urls = self.fal_client.generate_image(
            prompt=prompt,
            width=size,
            height=size,
            num_images=1,
        )

        # Download and save
        return self.fal_client.download_file(image_urls[0], output_path)
