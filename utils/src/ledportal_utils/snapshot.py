"""Snapshot processing utilities for LED Portal.

This module provides functions to convert and upscale LED matrix snapshot images
for better viewing and sharing.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def bmp_to_png(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Convert BMP snapshot to PNG format.

    Args:
        input_path: Path to input BMP file.
        output_path: Path to output PNG file. If None, uses input filename with .png extension.

    Returns:
        Path to the created PNG file.

    Example:
        >>> bmp_to_png("snapshot_20260211_120000.bmp")
        PosixPath('snapshot_20260211_120000.png')
    """
    input_path = Path(input_path)
    output_path = input_path.with_suffix(".png") if output_path is None else Path(output_path)

    # Open and convert
    img = Image.open(input_path)
    img.save(output_path, "PNG")

    return output_path


def upscale_pixelated(
    input_path: str | Path,
    output_path: str | Path | None = None,
    scale_factor: int = 10,
) -> Path:
    """Upscale snapshot with square pixel effect.

    Each original pixel becomes a scale_factor × scale_factor square, creating
    a pixelated LED display appearance.

    Args:
        input_path: Path to input image file (BMP or PNG).
        output_path: Path to output PNG file. If None, appends '_pixelated' to filename.
        scale_factor: Pixels per LED. Each original pixel becomes scale_factor × scale_factor.
            Default is 10 (64×32 becomes 640×320).

    Returns:
        Path to the created PNG file.

    Example:
        >>> upscale_pixelated("snapshot.bmp", scale_factor=10)
        PosixPath('snapshot_pixelated.png')
    """
    input_path = Path(input_path)
    output_path = (
        input_path.with_stem(f"{input_path.stem}_pixelated").with_suffix(".png")
        if output_path is None
        else Path(output_path)
    )

    # Open image
    img = Image.open(input_path)

    # Calculate new size
    new_width = img.width * scale_factor
    new_height = img.height * scale_factor

    # Resize using NEAREST neighbor - this creates crisp square pixels
    upscaled = img.resize((new_width, new_height), Image.Resampling.NEAREST)

    # Save as PNG
    upscaled.save(output_path, "PNG")

    return output_path


def upscale_led_circles(
    input_path: str | Path,
    output_path: str | Path | None = None,
    scale_factor: int = 10,
    led_size_ratio: float = 0.9,
    background_color: tuple[int, int, int] = (0, 0, 0),
) -> Path:
    """Upscale snapshot with circular LED effect.

    Each original pixel becomes a circle on a black background, mimicking the
    appearance of a real LED matrix display.

    Args:
        input_path: Path to input image file (BMP or PNG).
        output_path: Path to output PNG file. If None, appends '_led' to filename.
        scale_factor: Pixels per LED. Each original pixel becomes a
            scale_factor × scale_factor cell. Default is 10.
        led_size_ratio: Circle size relative to cell size (0.0-1.0).
            0.9 means circles are 90% of cell size, leaving small gaps.
            Default is 0.9.
        background_color: RGB tuple for background. Default is black (0, 0, 0).

    Returns:
        Path to the created PNG file.

    Example:
        >>> upscale_led_circles("snapshot.bmp", scale_factor=10, led_size_ratio=0.9)
        PosixPath('snapshot_led.png')
    """
    input_path = Path(input_path)
    output_path = (
        input_path.with_stem(f"{input_path.stem}_led").with_suffix(".png")
        if output_path is None
        else Path(output_path)
    )

    # Open and convert to RGB if needed
    img = Image.open(input_path).convert("RGB")

    # Convert to numpy array for pixel access
    pixels = np.array(img)
    height, width = pixels.shape[:2]

    # Create output image
    new_width = width * scale_factor
    new_height = height * scale_factor
    output = Image.new("RGB", (new_width, new_height), background_color)
    draw = ImageDraw.Draw(output)

    # Calculate circle radius
    radius = (scale_factor * led_size_ratio) / 2

    # Draw each LED as a circle
    for y in range(height):
        for x in range(width):
            # Get pixel color
            color = tuple(pixels[y, x])

            # Calculate center of this LED cell
            center_x = x * scale_factor + scale_factor / 2
            center_y = y * scale_factor + scale_factor / 2

            # Draw circle (ellipse with equal width/height)
            bbox = [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ]
            draw.ellipse(bbox, fill=color)

    # Save as PNG
    output.save(output_path, "PNG")

    return output_path
