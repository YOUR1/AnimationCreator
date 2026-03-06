"""High-quality GIF conversion using FFmpeg with proper chroma keying."""

import subprocess
import shutil
from pathlib import Path


class GifConverterFFmpeg:
    """Convert videos to high-quality transparent GIFs using FFmpeg."""

    def __init__(self):
        """Initialize and verify FFmpeg is available."""
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg not found. Install with: brew install ffmpeg")

    def convert(
        self,
        video_path: Path,
        output_path: Path,
        fps: int = 15,
        green_color: str = "0x00FF00",
        similarity: float = 0.3,
        blend: float = 0.1,
        scale: int | None = None,
    ) -> Path:
        """
        Convert video to transparent GIF with green screen removal.

        Uses FFmpeg's chromakey filter and palette generation for
        high-quality output.

        Args:
            video_path: Path to input video
            output_path: Path for output GIF
            fps: Target FPS
            green_color: Hex color to key out (default: pure green)
            similarity: Color similarity threshold (0-1, higher = more removal)
            blend: Edge blending (0-1, higher = softer edges)
            scale: Optional width to scale to (maintains aspect ratio)

        Returns:
            Path to the created GIF
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build filter chain
        filters = []

        # Scale if requested
        if scale:
            filters.append(f"scale={scale}:-1:flags=lanczos")

        # FPS
        filters.append(f"fps={fps}")

        # Chromakey - remove green and add alpha
        filters.append(f"chromakey={green_color}:{similarity}:{blend}")

        # Split for palette generation
        filter_complex = f"[0:v]{','.join(filters)},split[s0][s1];[s0]palettegen=reserve_transparent=1[p];[s1][p]paletteuse=alpha_threshold=128"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-lavfi", filter_complex,
            "-gifflags", "-offsetting",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        return output_path

    def convert_to_webm(
        self,
        video_path: Path,
        output_path: Path,
        green_color: str = "0x00FF00",
        similarity: float = 0.3,
        blend: float = 0.1,
    ) -> Path:
        """
        Convert video to WebM with true alpha channel.

        WebM/VP9 supports full alpha transparency (not binary like GIF).
        Better quality but less compatible than GIF.

        Args:
            video_path: Path to input video
            output_path: Path for output WebM
            green_color: Hex color to key out
            similarity: Color similarity threshold
            blend: Edge blending

        Returns:
            Path to the created WebM
        """
        output_path = output_path.with_suffix(".webm")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        filter_chain = f"chromakey={green_color}:{similarity}:{blend}"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", filter_chain,
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            "-b:v", "2M",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        return output_path

    def convert_to_png_sequence(
        self,
        video_path: Path,
        output_dir: Path,
        fps: int = 15,
        green_color: str = "0x00FF00",
        similarity: float = 0.3,
        blend: float = 0.1,
    ) -> Path:
        """
        Convert video to PNG sequence with transparency.

        PNG supports full alpha channel. Useful for game engines
        and professional video editing.

        Args:
            video_path: Path to input video
            output_dir: Directory for PNG frames
            fps: Frames per second to extract
            green_color: Hex color to key out
            similarity: Color similarity threshold
            blend: Edge blending

        Returns:
            Path to the output directory
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        filter_chain = f"fps={fps},chromakey={green_color}:{similarity}:{blend}"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", filter_chain,
            str(output_dir / "frame_%04d.png")
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        return output_dir


def test_conversion(video_path: str):
    """Test all conversion methods on a video."""
    converter = GifConverterFFmpeg()
    video = Path(video_path)
    base = video.parent / video.stem

    print("Testing FFmpeg GIF conversion...")

    # Test different similarity values
    for sim in [0.2, 0.3, 0.4]:
        output = base.parent / f"{video.stem}_ffmpeg_sim{sim}.gif"
        print(f"  Creating {output.name} (similarity={sim})...")
        converter.convert(video, output, similarity=sim, blend=0.1)

    # Test WebM with alpha
    output_webm = base.parent / f"{video.stem}_alpha.webm"
    print(f"  Creating {output_webm.name} (WebM with true alpha)...")
    converter.convert_to_webm(video, output_webm)

    # Test PNG sequence
    output_pngs = base.parent / f"{video.stem}_frames"
    print(f"  Creating PNG sequence in {output_pngs.name}/...")
    converter.convert_to_png_sequence(video, output_pngs, fps=10)

    print("Done! Check the output files.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_conversion(sys.argv[1])
    else:
        print("Usage: python gif_converter_ffmpeg.py <video_path>")
