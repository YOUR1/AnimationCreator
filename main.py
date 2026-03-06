#!/usr/bin/env python3
"""AI Animation Creator - Generate animated characters with transparent backgrounds."""

import sys
import re
import subprocess
import platform
from datetime import datetime
from pathlib import Path

import fal_client

from animation_creator import (
    Config,
    FalClient,
    CharacterGenerator,
    GreenScreenProcessor,
    Animator,
    GifConverter,
)
from animation_creator.video_processor import VideoProcessor
from animation_creator.spinner import Spinner


def print_header():
    """Print the application header."""
    print("\n" + "=" * 40)
    print("       AI Animation Creator")
    print("=" * 40 + "\n")


def get_character_description() -> str:
    """Prompt user for character description."""
    print("1. What character do you want to create?")
    description = input("   > ").strip()

    if not description:
        print("   Error: Please enter a character description.")
        return get_character_description()

    return description


def get_style_choice(config: Config) -> str:
    """Prompt user to select a style."""
    styles = config.list_styles()

    print("\n2. What style?")
    for i, (key, name) in enumerate(styles, 1):
        print(f"   [{i}] {name}")

    choice = input("   > ").strip()

    try:
        index = int(choice) - 1
        if 0 <= index < len(styles):
            return styles[index][0]
    except ValueError:
        pass

    print("   Error: Please enter a valid number.")
    return get_style_choice(config)


def get_animation_states(config: Config) -> list[str]:
    """Prompt user to select animation states."""
    states = config.list_animation_states()

    print("\n3. What animation states do you need? (comma-separated numbers)")
    for i, (key, name) in enumerate(states, 1):
        print(f"   [{i}] {name}")

    choice = input("   > ").strip()

    # Parse comma-separated numbers
    selected = []
    try:
        numbers = [int(n.strip()) for n in choice.split(",")]
        for num in numbers:
            if 1 <= num <= len(states):
                state_key = states[num - 1][0]
                if state_key not in selected:
                    selected.append(state_key)
    except ValueError:
        pass

    if not selected:
        print("   Error: Please enter valid numbers (e.g., 1,2,3)")
        return get_animation_states(config)

    return selected


def get_gif_option() -> bool:
    """Ask user if they want GIF conversion."""
    print("\n4. Convert videos to transparent GIFs?")
    print("   [1] Yes, create GIFs")
    print("   [2] No, keep MP4s only")

    choice = input("   > ").strip()

    return choice != "2"


def open_image_preview(image_path: Path):
    """Open image in system default viewer."""
    system = platform.system()
    if system == "Darwin":  # macOS
        subprocess.run(["open", str(image_path)], check=False)
    elif system == "Windows":
        subprocess.run(["start", "", str(image_path)], shell=True, check=False)
    else:  # Linux
        subprocess.run(["xdg-open", str(image_path)], check=False)


def preview_and_confirm(image_path: Path) -> bool:
    """
    Open image for preview and ask user to confirm.

    Returns:
        True if user approves, False to regenerate
    """
    print(f"\nOpening preview: {image_path.name}")
    open_image_preview(image_path)

    print("\nDoes the character look good?")
    print("   [1] Yes, continue with animations")
    print("   [2] No, generate a new version")

    choice = input("   > ").strip()

    return choice != "2"


def sanitize_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    # Remove special characters, replace spaces with underscores
    safe = re.sub(r"[^\w\s-]", "", name.lower())
    safe = re.sub(r"[-\s]+", "_", safe)
    return safe[:50]  # Limit length


def create_output_dir(character: str, style: str, base_dir: Path) -> Path:
    """Create a unique output directory for this generation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{sanitize_filename(character)}_{style}_{timestamp}"
    output_dir = base_dir / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def main():
    """Main entry point."""
    print_header()

    # Initialize configuration
    try:
        config = Config()
        # Validate API key early
        _ = config.fal_key
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Get user input
    character_description = get_character_description()
    style = get_style_choice(config)
    animation_states = get_animation_states(config)
    create_gifs = get_gif_option()

    # Create output directory
    output_dir = create_output_dir(
        character_description,
        style,
        config.DEFAULT_OUTPUT_DIR,
    )

    print(f"\nOutput will be saved to: {output_dir}\n")

    # Initialize components
    fal = FalClient(config)
    character_gen = CharacterGenerator(fal, config)
    green_screen = GreenScreenProcessor(config)
    animator = Animator(fal, config)
    gif_converter = GifConverter(config)

    spinner = Spinner()

    # Step 1: Generate character design (directly on green screen)
    # Loop until user approves the character
    version = 1
    approved = False

    while not approved:
        if version == 1:
            character_path = output_dir / "character.png"
        else:
            character_path = output_dir / f"character_v{version}.png"

        spinner.start(f"Generating character on green screen (v{version})...")
        character_gen.generate(
            character_description=character_description,
            style_key=style,
            output_path=character_path,
        )
        spinner.stop(f"Character saved: {character_path.name}")

        # Preview and ask for approval
        approved = preview_and_confirm(character_path)
        if not approved:
            version += 1
            print("   Regenerating...")

    # TODO: Green screen normalization disabled for now
    # spinner.start("Normalizing green screen background...")
    # green_screen.normalize_green_file(character_path)
    # spinner.stop("Green screen normalized to #00FF00")

    # Upload approved image for video generation
    spinner.start("Uploading image for animation...")
    image_url = fal_client.upload_file(str(character_path))
    spinner.stop("Image uploaded")

    # Step 3: Generate animations
    print("\nGenerating animations:")
    video_paths = {}
    for state in animation_states:
        state_name = config.ANIMATION_STATES[state]["name"]
        spinner.start(f"Generating {state_name} animation...")
        video_path = output_dir / f"{state}.mp4"
        animator.animate(
            image_url=image_url,
            character_description=character_description,
            animation_state=state,
            output_path=video_path,
        )
        video_paths[state] = video_path
        spinner.stop(f"{state_name} video saved: {video_path.name}")

    # Step 4: Apply ping-pong to videos for seamless looping
    print("\nApplying ping-pong loop to videos:")
    for state, video_path in video_paths.items():
        state_name = config.ANIMATION_STATES[state]["name"]
        spinner.start(f"Processing {state_name}...")
        VideoProcessor.make_ping_pong(video_path)
        spinner.stop(f"{state_name} ping-pong applied")

    # Step 5: Convert to transparent GIFs (optional)
    if create_gifs:
        print("\nConverting to transparent GIFs:")
        gif_paths = {}
        for state, video_path in video_paths.items():
            state_name = config.ANIMATION_STATES[state]["name"]
            spinner.start(f"Converting {state_name} to GIF...")
            gif_path = output_dir / f"{state}.gif"
            gif_converter.convert(video_path, gif_path)
            gif_paths[state] = gif_path
            spinner.stop(f"{state_name} GIF saved: {gif_path.name}")

    # Done
    print("\n" + "=" * 40)
    print("Done!")
    print(f"Output saved to: {output_dir}")
    print("=" * 40)

    # List generated files
    print("\nGenerated files:")
    for file in sorted(output_dir.iterdir()):
        print(f"  - {file.name}")


if __name__ == "__main__":
    main()
