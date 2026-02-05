"""Test pattern generation."""

from typing import TYPE_CHECKING

import numpy as np

from .color import convert_to_rgb565

if TYPE_CHECKING:
    from ..config import MatrixConfig


def create_test_pattern(matrix_config: MatrixConfig) -> bytes:
    """Create a gradient test pattern in RGB565 format.

    Creates a colorful gradient to verify USB communication and display:
    - Red gradient horizontally
    - Green gradient vertically
    - Blue constant

    Args:
        matrix_config: Matrix configuration with dimensions.

    Returns:
        RGB565 bytes for the test pattern.
    """
    width = matrix_config.width
    height = matrix_config.height

    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Create gradient pattern
    for y in range(height):
        for x in range(width):
            frame[y, x, 2] = int((x / width) * 255)  # Red (BGR order)
            frame[y, x, 1] = int((y / height) * 255)  # Green
            frame[y, x, 0] = 128  # Blue constant

    return convert_to_rgb565(frame)


def create_color_bars(matrix_config: MatrixConfig) -> bytes:
    """Create standard color bars test pattern.

    Creates vertical bars of: white, yellow, cyan, green, magenta, red, blue, black.

    Args:
        matrix_config: Matrix configuration with dimensions.

    Returns:
        RGB565 bytes for the color bars pattern.
    """
    width = matrix_config.width
    height = matrix_config.height

    # Standard color bars (BGR format)
    colors = [
        (255, 255, 255),  # White
        (0, 255, 255),  # Yellow
        (255, 255, 0),  # Cyan
        (0, 255, 0),  # Green
        (255, 0, 255),  # Magenta
        (0, 0, 255),  # Red
        (255, 0, 0),  # Blue
        (0, 0, 0),  # Black
    ]

    frame = np.zeros((height, width, 3), dtype=np.uint8)
    bar_width = width // len(colors)

    for i, color in enumerate(colors):
        x_start = i * bar_width
        x_end = (i + 1) * bar_width if i < len(colors) - 1 else width
        frame[:, x_start:x_end] = color

    return convert_to_rgb565(frame)


def create_solid_color(matrix_config: MatrixConfig, color: tuple[int, int, int]) -> bytes:
    """Create a solid color frame.

    Args:
        matrix_config: Matrix configuration with dimensions.
        color: BGR color tuple (0-255 for each channel).

    Returns:
        RGB565 bytes for the solid color frame.
    """
    width = matrix_config.width
    height = matrix_config.height

    frame = np.full((height, width, 3), color, dtype=np.uint8)

    return convert_to_rgb565(frame)


def create_checkerboard(
    matrix_config: MatrixConfig,
    cell_size: int = 4,
    color1: tuple[int, int, int] = (0, 0, 0),
    color2: tuple[int, int, int] = (255, 255, 255),
) -> bytes:
    """Create a checkerboard pattern.

    Args:
        matrix_config: Matrix configuration with dimensions.
        cell_size: Size of each cell in pixels.
        color1: First color (BGR).
        color2: Second color (BGR).

    Returns:
        RGB565 bytes for the checkerboard pattern.
    """
    width = matrix_config.width
    height = matrix_config.height

    frame = np.zeros((height, width, 3), dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            if ((x // cell_size) + (y // cell_size)) % 2 == 0:
                frame[y, x] = color1
            else:
                frame[y, x] = color2

    return convert_to_rgb565(frame)
