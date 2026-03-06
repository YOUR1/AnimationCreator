"""Video processing utilities."""

from pathlib import Path
import cv2
import numpy as np


class VideoProcessor:
    """Process video files."""

    @staticmethod
    def make_ping_pong(
        input_path: Path,
        output_path: Path | None = None,
    ) -> Path:
        """
        Create a ping-pong loop from a video (play forward then backward).

        Args:
            input_path: Path to input video
            output_path: Path to save (defaults to overwriting input)

        Returns:
            Path to the processed video
        """
        if output_path is None:
            output_path = input_path

        cap = cv2.VideoCapture(str(input_path))

        if not cap.isOpened():
            raise ValueError(f"Could not open video: {input_path}")

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Read all frames
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()

        if len(frames) < 2:
            raise ValueError("Video too short for ping-pong")

        # Create ping-pong: forward + reversed (excluding endpoints to avoid stutter)
        ping_pong_frames = frames + frames[-2:0:-1]

        # Write output
        temp_path = output_path.with_suffix('.tmp.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(temp_path), fourcc, fps, (width, height))

        for frame in ping_pong_frames:
            out.write(frame)
        out.release()

        # Replace original with processed (or move to output path)
        if temp_path != output_path:
            temp_path.replace(output_path)

        return output_path

    @staticmethod
    def get_video_info(video_path: Path) -> dict:
        """Get video information."""
        cap = cv2.VideoCapture(str(video_path))
        info = {
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        }
        info["duration"] = info["frame_count"] / info["fps"] if info["fps"] > 0 else 0
        cap.release()
        return info
