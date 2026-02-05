"""Frame resizing operations with display modes."""

from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from ..config import MatrixConfig, ProcessingConfig


# Map interpolation names to OpenCV constants
INTERPOLATION_MAP = {
    "nearest": cv2.INTER_NEAREST,
    "linear": cv2.INTER_LINEAR,
    "area": cv2.INTER_AREA,
    "cubic": cv2.INTER_CUBIC,
}

# Valid display modes
DISPLAY_MODES = ("landscape", "portrait", "squish", "letterbox")


def resize_frame(
    frame: NDArray[np.uint8],
    matrix_config: MatrixConfig,
    processing_config: ProcessingConfig | None = None,
    mode: str | None = None,
) -> NDArray[np.uint8]:
    """Crop and resize frame to matrix dimensions.

    Args:
        frame: Input BGR image as numpy array.
        matrix_config: Matrix configuration with target dimensions.
        processing_config: Processing configuration with interpolation setting.
        mode: Display mode override. If None, uses processing_config.display_mode.

    Returns:
        Resized BGR image as numpy array.

    Display Modes:
        - 'landscape': Crops to 2:1 aspect ratio from center, for horizontal matrix
        - 'portrait': Crops to 1:2 aspect ratio from center, rotates 90° for vertical
        - 'squish': No cropping, stretches entire frame to fit (may distort)
        - 'letterbox': No cropping, maintains aspect ratio, black bars fill empty space
    """
    interpolation_name = "linear"
    display_mode = "landscape"

    if processing_config is not None:
        interpolation_name = processing_config.interpolation
        display_mode = processing_config.display_mode

    if mode is not None:
        display_mode = mode

    interpolation = INTERPOLATION_MAP.get(interpolation_name, cv2.INTER_LINEAR)
    target_width = matrix_config.width
    target_height = matrix_config.height

    h, w = frame.shape[:2]

    if display_mode == "letterbox":
        return _resize_letterbox(frame, target_width, target_height, interpolation)
    elif display_mode == "squish":
        return cv2.resize(frame, (target_width, target_height), interpolation=interpolation)
    elif display_mode == "portrait":
        return _resize_portrait(frame, target_width, target_height, interpolation)
    else:  # "landscape" (default)
        return _resize_landscape(frame, target_width, target_height, interpolation)


def _resize_landscape(
    frame: NDArray[np.uint8],
    target_width: int,
    target_height: int,
    interpolation: int,
) -> NDArray[np.uint8]:
    """Crop to 2:1 aspect ratio from center, for horizontal matrix."""
    h, w = frame.shape[:2]

    # Crop to 2:1 aspect ratio from center
    # Keep full width, crop height to half of width
    target_h = w // 2
    if target_h > h:
        target_h = h

    # Center crop vertically
    start_y = (h - target_h) // 2
    cropped = frame[start_y : start_y + target_h, 0:w]

    # Resize to matrix dimensions
    return cv2.resize(cropped, (target_width, target_height), interpolation=interpolation)


def _resize_portrait(
    frame: NDArray[np.uint8],
    target_width: int,
    target_height: int,
    interpolation: int,
) -> NDArray[np.uint8]:
    """Crop to 1:2 aspect ratio from center, rotates 90° for vertical matrix."""
    h, w = frame.shape[:2]

    # Crop to 1:2 aspect ratio (tall and narrow) from center
    # Keep full height, crop width to half of height
    target_w = h // 2
    if target_w > w:
        target_w = w

    # Center crop horizontally
    start_x = (w - target_w) // 2
    cropped = frame[0:h, start_x : start_x + target_w]

    # Resize to swapped dimensions (height x width), then rotate 90° clockwise
    resized = cv2.resize(cropped, (target_height, target_width), interpolation=interpolation)

    # Rotate 90° clockwise for portrait orientation
    return cv2.rotate(resized, cv2.ROTATE_90_CLOCKWISE)


def _resize_letterbox(
    frame: NDArray[np.uint8],
    target_width: int,
    target_height: int,
    interpolation: int,
) -> NDArray[np.uint8]:
    """Maintain aspect ratio, center on black background."""
    h, w = frame.shape[:2]

    # Calculate scale to fit within matrix dimensions
    scale_w = target_width / w
    scale_h = target_height / h
    scale = min(scale_w, scale_h)  # Use smaller scale to fit entirely

    # Calculate new dimensions
    new_w = int(w * scale)
    new_h = int(h * scale)

    # Resize proportionally
    resized = cv2.resize(frame, (new_w, new_h), interpolation=interpolation)

    # Create black canvas
    canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)

    # Calculate centering offsets
    x_offset = (target_width - new_w) // 2
    y_offset = (target_height - new_h) // 2

    # Place resized image on canvas
    canvas[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = resized

    return canvas
