"""AI Animation Creator - Generate animated characters with transparent backgrounds."""

# Lazy imports to avoid slow startup from rembg model loading
def __getattr__(name):
    if name == "Config":
        from .config import Config
        return Config
    elif name == "FalClient":
        from .fal_client import FalClient
        return FalClient
    elif name == "CharacterGenerator":
        from .character_generator import CharacterGenerator
        return CharacterGenerator
    elif name == "GreenScreenProcessor":
        from .green_screen import GreenScreenProcessor
        return GreenScreenProcessor
    elif name == "Animator":
        from .animator import Animator
        return Animator
    elif name == "GifConverter":
        from .gif_converter import GifConverter
        return GifConverter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Config",
    "FalClient",
    "CharacterGenerator",
    "GreenScreenProcessor",
    "Animator",
    "GifConverter",
]
