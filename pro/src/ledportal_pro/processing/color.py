"""Color conversion and manipulation operations."""

import cv2
import numpy as np
from numpy.typing import NDArray


def convert_to_rgb565(frame: NDArray[np.uint8]) -> bytes:
    """Convert BGR frame to RGB565 format.

    RGB565 format uses 16 bits per pixel:
    - 5 bits for red (bits 11-15)
    - 6 bits for green (bits 5-10)
    - 5 bits for blue (bits 0-4)

    Args:
        frame: BGR image as numpy array with shape (height, width, 3).

    Returns:
        Bytes array in RGB565 format, little-endian byte order.
    """
    # Convert BGR to RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Extract and convert color channels
    r = (rgb[:, :, 0] >> 3).astype(np.uint16)  # 5 bits (0-31)
    g = (rgb[:, :, 1] >> 2).astype(np.uint16)  # 6 bits (0-63)
    b = (rgb[:, :, 2] >> 3).astype(np.uint16)  # 5 bits (0-31)

    # Pack into RGB565 format
    rgb565 = (r << 11) | (g << 5) | b

    # Convert to bytes (little-endian)
    return rgb565.astype("<u2").tobytes()


def apply_grayscale(frame: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Convert BGR frame to grayscale (black and white).

    Returns a BGR frame where all channels have the same grayscale value,
    maintaining compatibility with the rest of the pipeline.

    Args:
        frame: BGR image as numpy array.

    Returns:
        BGR image where R=G=B (grayscale appearance).
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def apply_gamma_correction(frame: NDArray[np.uint8], gamma: float = 2.2) -> NDArray[np.uint8]:
    """Apply gamma correction for better LED display appearance.

    LEDs have different response characteristics than monitors,
    so gamma correction can improve perceived image quality.

    Args:
        frame: BGR image as numpy array.
        gamma: Gamma value (typically 2.2 for LED matrices).

    Returns:
        Gamma-corrected BGR image.
    """
    # Build lookup table for efficiency
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)

    return cv2.LUT(frame, table)


def rgb565_to_bgr(data: bytes, width: int, height: int) -> NDArray[np.uint8]:
    """Convert RGB565 bytes back to BGR image.

    Useful for debugging and verification.

    Args:
        data: RGB565 bytes in little-endian format.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        BGR image as numpy array.
    """
    # Parse RGB565 data
    rgb565 = np.frombuffer(data, dtype="<u2").reshape((height, width))

    # Extract channels
    r = ((rgb565 >> 11) & 0x1F) << 3
    g = ((rgb565 >> 5) & 0x3F) << 2
    b = (rgb565 & 0x1F) << 3

    # Stack into BGR format
    bgr = np.stack([b, g, r], axis=-1).astype(np.uint8)

    return bgr
