"""Configuration management for AnimationCreator."""

import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Manages configuration and API keys."""

    # fal.ai model endpoints
    FLUX_MODEL = "fal-ai/flux-pro/v1.1"
    KLING_MODEL = "fal-ai/kling-video/v1.6/pro/image-to-video"

    # Style presets with optimized prompts
    STYLES = {
        "kawaii": {
            "name": "Kawaii/Cute cartoon",
            "prompt": "cute kawaii style, simple shapes, pastel colors, big eyes, adorable, chibi proportions",
        },
        "pixar": {
            "name": "Pixar 3D style",
            "prompt": "Pixar 3D render style, smooth surfaces, expressive, high quality CGI, subsurface scattering",
        },
        "realistic": {
            "name": "Realistic",
            "prompt": "photorealistic, detailed, natural lighting, high detail, cinematic",
        },
        "pixel": {
            "name": "Pixel art",
            "prompt": "pixel art style, 16-bit, retro game aesthetic, clean pixels, sprite style",
        },
        "watercolor": {
            "name": "Watercolor illustration",
            "prompt": "watercolor illustration, soft edges, artistic, painted texture, gentle colors",
        },
    }

    # Animation state prompts - optimized for green screen compositing
    # Key: no floor, no shadows, no reflections, floating character, solid flat green
    ANIMATION_STATES = {
        "idle": {
            "name": "Idle",
            "prompt": "subtle breathing motion, slight idle movement, gentle sway, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
        "walk": {
            "name": "Walk",
            "prompt": "walking cycle, forward walking motion, arms swinging naturally, smooth stride, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
        "run": {
            "name": "Run",
            "prompt": "running cycle, fast running motion, dynamic arm movement, energetic stride, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
        "jump": {
            "name": "Jump",
            "prompt": "jumping motion, jump up and land, bouncy movement, legs bending, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
        "attack": {
            "name": "Attack",
            "prompt": "attack motion, striking pose, combat movement, dynamic action, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
        "dancing": {
            "name": "Dancing/Happy",
            "prompt": "dancing happily, rhythmic bouncing, joyful movement, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
        "sad": {
            "name": "Sad/Game over",
            "prompt": "looks sad, gentle swaying, disappointed expression, subtle movement, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
        "excited": {
            "name": "Excited/Level up",
            "prompt": "bouncing with excitement, celebrating, energetic movement, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
        "custom": {
            "name": "Custom",
            "prompt": "smooth motion, character floating in center, flat solid bright green background, chroma key green screen, evenly lit, studio lighting",
        },
    }

    # Default negative prompt for animations (things to avoid)
    DEFAULT_NEGATIVE_PROMPT = "shadows, dark areas, floor, ground, reflections, multiple characters, blurry, distorted"

    # Valid durations for Kling AI
    VALID_DURATIONS = [5, 10]

    # Valid aspect ratios for Kling AI
    VALID_ASPECT_RATIOS = ["1:1", "16:9", "9:16"]

    # Valid special effects
    VALID_SPECIAL_FX = ["hug", "kiss", "heart_gesture", "squish", "expansion"]

    # Green screen color
    GREEN_SCREEN_COLOR = (0, 255, 0)  # Pure green #00FF00

    # Output settings
    DEFAULT_OUTPUT_DIR = Path("output")
    GIF_FPS = 25
    VIDEO_DURATION = 5  # seconds

    def __init__(self):
        """Initialize configuration and load environment variables."""
        load_dotenv()
        self._fal_key = os.getenv("FAL_KEY")

    @property
    def fal_key(self) -> str:
        """Get fal.ai API key."""
        if not self._fal_key:
            raise ValueError(
                "FAL_KEY not found. Please set it in your .env file.\n"
                "Get your key from: https://fal.ai/dashboard/keys"
            )
        return self._fal_key

    def get_style_prompt(self, style_key: str) -> str:
        """Get the prompt modifier for a style."""
        if style_key not in self.STYLES:
            raise ValueError(f"Unknown style: {style_key}")
        return self.STYLES[style_key]["prompt"]

    def get_animation_prompt(self, state_key: str) -> str:
        """Get the animation prompt for a state."""
        if state_key not in self.ANIMATION_STATES:
            raise ValueError(f"Unknown animation state: {state_key}")
        return self.ANIMATION_STATES[state_key]["prompt"]

    @classmethod
    def list_styles(cls) -> list[tuple[str, str]]:
        """List available styles as (key, display_name) tuples."""
        return [(key, style["name"]) for key, style in cls.STYLES.items()]

    @classmethod
    def list_animation_states(cls) -> list[tuple[str, str]]:
        """List available animation states as (key, display_name) tuples."""
        return [(key, state["name"]) for key, state in cls.ANIMATION_STATES.items()]
