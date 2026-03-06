"""
Asset utility functions for image processing and validation.

This module provides utilities for:
- Image thumbnail generation
- GIF optimization
- File type validation
- File size validation
"""

import io
import logging
import mimetypes
from typing import Optional, Tuple

from PIL import Image, ImageSequence

logger = logging.getLogger(__name__)

# Allowed file types with their extensions and MIME types
ALLOWED_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

ALLOWED_VIDEO_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}

ALLOWED_TYPES = {**ALLOWED_IMAGE_TYPES, **ALLOWED_VIDEO_TYPES}

# Size limits (in bytes)
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_VIDEO_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_GIF_SIZE = 100 * 1024 * 1024  # 100 MB

# Thumbnail settings
THUMBNAIL_SIZES = {
    "small": (150, 150),
    "medium": (300, 300),
    "large": (600, 600),
}
THUMBNAIL_QUALITY = 85


class ValidationError(Exception):
    """Raised when file validation fails."""
    pass


class ProcessingError(Exception):
    """Raised when file processing fails."""
    pass


def validate_file_type(
    filename: str,
    content_type: Optional[str] = None,
    allowed_types: Optional[dict] = None
) -> Tuple[str, str]:
    """
    Validate file type based on extension and content type.

    Args:
        filename: Name of the file
        content_type: MIME type provided with the file
        allowed_types: Dictionary of allowed extensions and MIME types

    Returns:
        Tuple of (extension, mime_type)

    Raises:
        ValidationError: If file type is not allowed
    """
    if allowed_types is None:
        allowed_types = ALLOWED_TYPES

    # Extract extension
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    if not ext:
        raise ValidationError("File must have an extension")

    if ext not in allowed_types:
        allowed = ", ".join(allowed_types.keys())
        raise ValidationError(f"File type '{ext}' not allowed. Allowed types: {allowed}")

    expected_mime = allowed_types[ext]

    # Validate content type if provided
    if content_type:
        # Normalize content type (remove parameters like charset)
        normalized_type = content_type.split(";")[0].strip().lower()

        if normalized_type != expected_mime:
            # Allow some flexibility for JPEG variants
            if not (ext in [".jpg", ".jpeg"] and normalized_type in ["image/jpeg", "image/jpg"]):
                logger.warning(
                    f"Content type mismatch: expected {expected_mime}, got {normalized_type}"
                )

    return ext, expected_mime


def validate_file_size(
    file_bytes: bytes,
    filename: str,
    max_size: Optional[int] = None
) -> int:
    """
    Validate file size.

    Args:
        file_bytes: File content as bytes
        filename: Name of the file (used to determine type-specific limits)
        max_size: Override maximum size in bytes

    Returns:
        Size of the file in bytes

    Raises:
        ValidationError: If file size exceeds limit
    """
    size = len(file_bytes)

    if max_size is None:
        # Determine limit based on file type
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()

        if ext == ".gif":
            max_size = MAX_GIF_SIZE
        elif ext in ALLOWED_VIDEO_TYPES:
            max_size = MAX_VIDEO_SIZE
        else:
            max_size = MAX_IMAGE_SIZE

    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        size_mb = size / (1024 * 1024)
        raise ValidationError(
            f"File size ({size_mb:.1f} MB) exceeds maximum allowed ({max_mb:.1f} MB)"
        )

    return size


def validate_image_dimensions(
    file_bytes: bytes,
    max_width: int = 8192,
    max_height: int = 8192,
    min_width: int = 10,
    min_height: int = 10
) -> Tuple[int, int]:
    """
    Validate image dimensions.

    Args:
        file_bytes: Image content as bytes
        max_width: Maximum allowed width
        max_height: Maximum allowed height
        min_width: Minimum required width
        min_height: Minimum required height

    Returns:
        Tuple of (width, height)

    Raises:
        ValidationError: If dimensions are invalid
    """
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            width, height = img.size

            if width > max_width or height > max_height:
                raise ValidationError(
                    f"Image dimensions ({width}x{height}) exceed maximum "
                    f"({max_width}x{max_height})"
                )

            if width < min_width or height < min_height:
                raise ValidationError(
                    f"Image dimensions ({width}x{height}) below minimum "
                    f"({min_width}x{min_height})"
                )

            return width, height

    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Failed to read image dimensions: {e}")


def generate_thumbnail(
    file_bytes: bytes,
    size: str = "medium",
    output_format: str = "webp"
) -> bytes:
    """
    Generate a thumbnail from an image.

    Args:
        file_bytes: Original image content as bytes
        size: Thumbnail size ('small', 'medium', 'large')
        output_format: Output format ('webp', 'jpeg', 'png')

    Returns:
        Thumbnail image as bytes

    Raises:
        ProcessingError: If thumbnail generation fails
    """
    if size not in THUMBNAIL_SIZES:
        raise ProcessingError(f"Invalid thumbnail size: {size}")

    target_size = THUMBNAIL_SIZES[size]

    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            # Convert to RGB if necessary (for JPEG/WebP output)
            if output_format.lower() in ["jpeg", "jpg", "webp"]:
                if img.mode in ("RGBA", "P"):
                    # Create white background for transparency
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

            # Create thumbnail (maintains aspect ratio)
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()

            save_kwargs = {"optimize": True}
            if output_format.lower() in ["jpeg", "jpg"]:
                save_format = "JPEG"
                save_kwargs["quality"] = THUMBNAIL_QUALITY
            elif output_format.lower() == "webp":
                save_format = "WEBP"
                save_kwargs["quality"] = THUMBNAIL_QUALITY
            else:
                save_format = "PNG"

            img.save(output, format=save_format, **save_kwargs)
            output.seek(0)

            logger.debug(f"Generated {size} thumbnail ({target_size})")
            return output.read()

    except Exception as e:
        logger.error(f"Failed to generate thumbnail: {e}")
        raise ProcessingError(f"Failed to generate thumbnail: {e}")


def generate_all_thumbnails(file_bytes: bytes, output_format: str = "webp") -> dict:
    """
    Generate all thumbnail sizes for an image.

    Args:
        file_bytes: Original image content as bytes
        output_format: Output format ('webp', 'jpeg', 'png')

    Returns:
        Dictionary mapping size names to thumbnail bytes
    """
    thumbnails = {}

    for size_name in THUMBNAIL_SIZES.keys():
        try:
            thumbnails[size_name] = generate_thumbnail(
                file_bytes, size_name, output_format
            )
        except ProcessingError as e:
            logger.warning(f"Failed to generate {size_name} thumbnail: {e}")

    return thumbnails


def optimize_gif(
    file_bytes: bytes,
    max_colors: int = 256,
    optimize_frames: bool = True,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None
) -> bytes:
    """
    Optimize a GIF file for smaller size.

    Args:
        file_bytes: GIF content as bytes
        max_colors: Maximum number of colors (2-256)
        optimize_frames: Whether to optimize frame differences
        max_width: Maximum width (resize if larger)
        max_height: Maximum height (resize if larger)

    Returns:
        Optimized GIF as bytes

    Raises:
        ProcessingError: If optimization fails
    """
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            if img.format != "GIF":
                raise ProcessingError("File is not a GIF")

            frames = []
            durations = []

            # Extract all frames
            for frame in ImageSequence.Iterator(img):
                frame_copy = frame.copy()

                # Resize if needed
                if max_width or max_height:
                    width, height = frame_copy.size
                    resize_needed = False

                    if max_width and width > max_width:
                        resize_needed = True
                        ratio = max_width / width
                        width = max_width
                        height = int(height * ratio)

                    if max_height and height > max_height:
                        resize_needed = True
                        ratio = max_height / height
                        height = max_height
                        width = int(width * ratio)

                    if resize_needed:
                        frame_copy = frame_copy.resize(
                            (width, height),
                            Image.Resampling.LANCZOS
                        )

                # Reduce colors if needed
                if max_colors < 256:
                    frame_copy = frame_copy.quantize(colors=max_colors)

                frames.append(frame_copy)

                # Get frame duration
                duration = frame.info.get("duration", 100)
                durations.append(duration)

            # Save optimized GIF
            output = io.BytesIO()

            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=img.info.get("loop", 0),
                optimize=optimize_frames
            )

            output.seek(0)
            optimized = output.read()

            original_size = len(file_bytes)
            new_size = len(optimized)
            reduction = ((original_size - new_size) / original_size) * 100

            logger.info(
                f"GIF optimized: {original_size} -> {new_size} bytes "
                f"({reduction:.1f}% reduction)"
            )

            return optimized

    except ProcessingError:
        raise
    except Exception as e:
        logger.error(f"Failed to optimize GIF: {e}")
        raise ProcessingError(f"Failed to optimize GIF: {e}")


def convert_image_format(
    file_bytes: bytes,
    output_format: str,
    quality: int = 85
) -> bytes:
    """
    Convert an image to a different format.

    Args:
        file_bytes: Original image content as bytes
        output_format: Target format ('webp', 'jpeg', 'png')
        quality: Quality for lossy formats (1-100)

    Returns:
        Converted image as bytes

    Raises:
        ProcessingError: If conversion fails
    """
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            # Handle transparency for formats that don't support it
            if output_format.lower() in ["jpeg", "jpg"]:
                if img.mode in ("RGBA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                save_format = "JPEG"
            elif output_format.lower() == "webp":
                save_format = "WEBP"
            elif output_format.lower() == "png":
                save_format = "PNG"
            else:
                raise ProcessingError(f"Unsupported output format: {output_format}")

            output = io.BytesIO()

            save_kwargs = {"optimize": True}
            if save_format in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality

            img.save(output, format=save_format, **save_kwargs)
            output.seek(0)

            return output.read()

    except ProcessingError:
        raise
    except Exception as e:
        logger.error(f"Failed to convert image: {e}")
        raise ProcessingError(f"Failed to convert image: {e}")


def get_image_info(file_bytes: bytes) -> dict:
    """
    Get information about an image.

    Args:
        file_bytes: Image content as bytes

    Returns:
        Dictionary with image information
    """
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            info = {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": len(file_bytes),
            }

            # Check if animated GIF
            if img.format == "GIF":
                try:
                    frames = 0
                    for _ in ImageSequence.Iterator(img):
                        frames += 1
                    info["is_animated"] = frames > 1
                    info["frame_count"] = frames
                except Exception:
                    info["is_animated"] = False
                    info["frame_count"] = 1

            return info

    except Exception as e:
        logger.error(f"Failed to get image info: {e}")
        return {"error": str(e), "size_bytes": len(file_bytes)}


def validate_and_process_upload(
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str] = None,
    generate_thumbnails: bool = True
) -> dict:
    """
    Validate and process an uploaded file.

    Args:
        file_bytes: File content as bytes
        filename: Original filename
        content_type: MIME type of the file
        generate_thumbnails: Whether to generate thumbnails for images

    Returns:
        Dictionary with processed file data and metadata

    Raises:
        ValidationError: If validation fails
    """
    # Validate file type
    ext, mime_type = validate_file_type(filename, content_type)

    # Validate file size
    size = validate_file_size(file_bytes, filename)

    result = {
        "filename": filename,
        "extension": ext,
        "content_type": mime_type,
        "size_bytes": size,
        "file_bytes": file_bytes,
    }

    # For images, get additional info and optionally generate thumbnails
    if ext in ALLOWED_IMAGE_TYPES:
        width, height = validate_image_dimensions(file_bytes)
        result["width"] = width
        result["height"] = height

        image_info = get_image_info(file_bytes)
        result["image_info"] = image_info

        if generate_thumbnails and ext != ".gif":
            result["thumbnails"] = generate_all_thumbnails(file_bytes)

    return result
