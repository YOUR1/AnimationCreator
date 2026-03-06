"""Convert MP4 videos to transparent GIFs with green screen removal."""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image

from .config import Config


class GifConverter:
    """Converts videos to transparent GIFs with chroma key removal."""

    def __init__(self, config: Config):
        """Initialize the GIF converter."""
        self.config = config
        self.target_fps = config.GIF_FPS

    def extract_frames(
        self,
        video_path: Path,
        max_fps: int | None = None,
    ) -> tuple[list[np.ndarray], float]:
        """
        Extract frames from a video file.

        Args:
            video_path: Path to the video file
            max_fps: Maximum FPS to extract (None = use video's native FPS)

        Returns:
            Tuple of (frames list, actual FPS of extracted frames)
        """
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS)

        # Calculate frame interval to achieve target FPS
        if max_fps and max_fps < video_fps:
            frame_interval = max(1, round(video_fps / max_fps))
            actual_fps = video_fps / frame_interval
        else:
            frame_interval = 1
            actual_fps = video_fps

        frames = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                frames.append(frame)

            frame_count += 1

        cap.release()
        return frames, actual_fps

    def apply_chroma_key(
        self,
        frame: np.ndarray,
        edge_erode: int = 2,
        softness: int = 3,
    ) -> Image.Image:
        """
        Remove green screen from a frame.

        Args:
            frame: BGR frame from OpenCV
            edge_erode: Pixels to erode from edges to remove green fringing
            softness: Edge softness for smoother transparency

        Returns:
            PIL Image with transparent background (RGBA)
        """
        # Convert BGR to RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to HSV for better green detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Core green screen detection - tight range for pure green background
        # This catches the main green screen area
        lower_green_core = np.array([35, 100, 100])
        upper_green_core = np.array([85, 255, 255])
        core_mask = cv2.inRange(hsv, lower_green_core, upper_green_core)

        # Edge green detection - wider range but only near existing green areas
        # This catches green fringing at edges
        lower_green_edge = np.array([30, 50, 50])
        upper_green_edge = np.array([90, 255, 255])
        edge_mask = cv2.inRange(hsv, lower_green_edge, upper_green_edge)

        # Dilate core mask slightly, then AND with edge mask
        # This only catches edge greens that are adjacent to the main green screen
        dilated_core = cv2.dilate(core_mask, np.ones((5, 5), np.uint8), iterations=2)
        edge_only = edge_mask & dilated_core

        # Combine: core green + adjacent edge green
        green_mask = core_mask | edge_only

        # Small dilation to clean up fringing
        if edge_erode > 0:
            dilate_kernel = np.ones((edge_erode * 2 + 1, edge_erode * 2 + 1), np.uint8)
            green_mask = cv2.dilate(green_mask, dilate_kernel, iterations=1)

        # Clean up small noise
        kernel = np.ones((3, 3), np.uint8)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)

        # Blur the mask edges for smoother transparency
        if softness > 0:
            green_mask = cv2.GaussianBlur(green_mask, (softness * 2 + 1, softness * 2 + 1), 0)

        # Invert mask (we want to keep non-green areas)
        alpha = 255 - green_mask

        # Gentle despill: only reduce green on edge pixels that are very green-dominant
        edge_pixels = (alpha > 20) & (alpha < 235)
        b, g, r = rgb[:, :, 2], rgb[:, :, 1], rgb[:, :, 0]
        very_green = edge_pixels & (g > r + 30) & (g > b + 30)

        rgb_float = rgb.astype(np.float32)
        rgb_float[very_green, 1] = np.minimum(
            rgb_float[very_green, 1],
            np.maximum(rgb_float[very_green, 0], rgb_float[very_green, 2]) + 10
        )
        rgb = rgb_float.astype(np.uint8)

        # Create RGBA image
        rgba = np.dstack((rgb, alpha))

        return Image.fromarray(rgba, mode="RGBA")

    def create_gif(
        self,
        frames: list[Image.Image],
        output_path: Path,
        fps: float = 15,
        optimize: bool = True,
        ping_pong: bool = False,
    ) -> Path:
        """
        Create an animated GIF from frames.

        Args:
            frames: List of PIL Images (RGBA)
            output_path: Path to save the GIF
            fps: Frames per second
            optimize: Whether to optimize the GIF
            ping_pong: If True, play forward then backward for seamless loop

        Returns:
            Path to the saved GIF
        """
        if not frames:
            raise ValueError("No frames to create GIF")

        # Create ping-pong loop (forward + backward, excluding duplicate endpoints)
        if ping_pong and len(frames) > 2:
            frames = frames + frames[-2:0:-1]  # Add reversed frames, excluding first and last

        # Calculate frame duration in milliseconds
        # GIF minimum is 10ms (100fps), but most players struggle below 20ms
        duration = max(20, int(1000 / fps))

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as animated GIF
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,  # Loop forever
            disposal=2,  # Clear frame before rendering next
            optimize=optimize,
        )

        return output_path

    def convert(
        self,
        video_path: Path,
        output_path: Path,
        max_fps: int = 60,
        edge_erode: int = 2,
        ping_pong: bool = False,
    ) -> Path:
        """
        Convert a video to a transparent GIF.

        Args:
            video_path: Path to the input video (MP4)
            output_path: Path to save the output GIF
            max_fps: Maximum FPS for the GIF (lower = smaller file)
            edge_erode: Pixels to erode from edges (higher = more green removed)
            ping_pong: If True, play forward then backward for seamless loop

        Returns:
            Path to the saved GIF
        """
        # Extract frames at video's native FPS (capped at max_fps)
        bgr_frames, actual_fps = self.extract_frames(video_path, max_fps)

        # Apply chroma key to each frame
        rgba_frames = [
            self.apply_chroma_key(frame, edge_erode=edge_erode)
            for frame in bgr_frames
        ]

        # Create GIF with correct timing
        return self.create_gif(rgba_frames, output_path, fps=actual_fps, ping_pong=ping_pong)

    def convert_all(
        self,
        video_paths: dict[str, Path],
        output_dir: Path,
        fps: int | None = None,
        progress_callback: callable = None,
    ) -> dict[str, Path]:
        """
        Convert multiple videos to GIFs.

        Args:
            video_paths: Dictionary mapping state keys to video paths
            output_dir: Directory to save GIFs
            fps: Target FPS
            progress_callback: Optional callback(state_name) for progress

        Returns:
            Dictionary mapping state keys to GIF paths
        """
        results = {}

        for state, video_path in video_paths.items():
            if progress_callback:
                progress_callback(state)

            gif_path = output_dir / f"{state}.gif"
            results[state] = self.convert(video_path, gif_path, fps)

        return results
