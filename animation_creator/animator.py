"""Video animation generation using fal.ai Kling model."""

from pathlib import Path

from .config import Config
from .fal_client import FalClient


class Animator:
    """Generates character animations using fal.ai video models."""

    def __init__(self, fal_client: FalClient, config: Config):
        """Initialize the animator."""
        self.fal_client = fal_client
        self.config = config

    def build_animation_prompt(
        self,
        character_description: str,
        animation_state: str,
        custom_prompt: str | None = None,
    ) -> str:
        """
        Build animation prompt for a specific state.

        Args:
            character_description: Description of the character
            animation_state: Animation state key (idle, walk, run, jump, attack, etc.)
            custom_prompt: Optional custom prompt to append/use for custom animations

        Returns:
            Complete animation prompt
        """
        state_prompt = self.config.get_animation_prompt(animation_state)

        # For custom animations, use the custom prompt as the main action
        if animation_state == "custom" and custom_prompt:
            prompt = (
                f"{character_description}, {custom_prompt}, {state_prompt}, "
                "smooth motion, seamless loop, consistent character, "
                "solid bright green background #00FF00"
            )
        else:
            # Append custom prompt if provided (for additional guidance)
            extra = f", {custom_prompt}" if custom_prompt else ""
            prompt = (
                f"{character_description}, {state_prompt}{extra}, "
                "smooth motion, seamless loop, consistent character, "
                "solid bright green background #00FF00"
            )

        return prompt

    def animate(
        self,
        image_url: str,
        character_description: str,
        animation_state: str,
        output_path: Path,
        duration: int = 5,
        aspect_ratio: str = "1:1",
        custom_prompt: str | None = None,
        negative_prompt: str | None = None,
        cfg_scale: float | None = None,
        static_mask_url: str | None = None,
        dynamic_mask_url: str | None = None,
        special_fx: str | None = None,
    ) -> Path:
        """
        Generate an animation for a character.

        Args:
            image_url: URL of the character image (on green screen)
            character_description: Description of the character for context
            animation_state: Animation state to generate
            output_path: Path to save the video
            duration: Video duration in seconds (5 or 10)
            aspect_ratio: Video aspect ratio (1:1, 16:9, 9:16)
            custom_prompt: Optional custom prompt for the animation
            negative_prompt: Elements to avoid in generation
            cfg_scale: Classifier Free Guidance scale
            static_mask_url: URL for static motion brush mask
            dynamic_mask_url: URL for dynamic motion brush mask
            special_fx: Special effects (hug, kiss, heart_gesture, squish, expansion)

        Returns:
            Path to the saved video file
        """
        prompt = self.build_animation_prompt(
            character_description, animation_state, custom_prompt
        )

        # Use default negative prompt if none provided
        final_negative_prompt = negative_prompt or self.config.DEFAULT_NEGATIVE_PROMPT

        # Generate video
        video_url = self.fal_client.generate_video(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            negative_prompt=final_negative_prompt,
            cfg_scale=cfg_scale,
            static_mask_url=static_mask_url,
            dynamic_mask_url=dynamic_mask_url,
            special_fx=special_fx,
        )

        # Download and save
        return self.fal_client.download_file(video_url, output_path)

    def animate_all_states(
        self,
        image_url: str,
        character_description: str,
        states: list[str],
        output_dir: Path,
        duration: int = 5,
        progress_callback: callable = None,
    ) -> dict[str, Path]:
        """
        Generate animations for multiple states.

        Args:
            image_url: URL of the character image
            character_description: Description of the character
            states: List of animation state keys to generate
            output_dir: Directory to save videos
            duration: Video duration in seconds
            progress_callback: Optional callback(state_name) for progress updates

        Returns:
            Dictionary mapping state keys to video file paths
        """
        results = {}

        for state in states:
            if progress_callback:
                state_name = self.config.ANIMATION_STATES[state]["name"]
                progress_callback(state_name)

            output_path = output_dir / f"{state}.mp4"
            video_path = self.animate(
                image_url=image_url,
                character_description=character_description,
                animation_state=state,
                output_path=output_path,
                duration=duration,
            )
            results[state] = video_path

        return results
