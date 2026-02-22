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

# Valid orientations and processing modes
ORIENTATIONS = ("landscape", "portrait")
PROCESSING_MODES = ("center", "stretch", "fit")


def resize_frame(
    frame: NDArray[np.uint8],
    matrix_config: MatrixConfig,
    processing_config: ProcessingConfig | None = None,
    orientation: str | None = None,
    processing_mode: str | None = None,
) -> NDArray[np.uint8]:
    """Crop and resize frame to matrix dimensions.

    Args:
        frame: Input BGR image as numpy array.
        matrix_config: Matrix configuration with target dimensions.
        processing_config: Processing configuration with interpolation setting.
        orientation: Orientation override ("landscape" or "portrait").
        processing_mode: Processing mode override ("center", "stretch", or "fit").

    Returns:
        Resized BGR image as numpy array.

    Orientations:
        - 'landscape': Horizontal display (64x32), no rotation
        - 'portrait': Vertical display (rotates 90° clockwise)

    Processing Modes:
        - 'center': Crops from center, clips edges based on orientation
        - 'stretch': Stretches entire frame to fit (may distort)
        - 'fit': Scales to fit with black bars (letterbox)
    """
    interpolation_name = "linear"
    current_orientation = "landscape"
    current_processing_mode = "center"

    if processing_config is not None:
        interpolation_name = processing_config.interpolation
        current_orientation = processing_config.orientation
        current_processing_mode = processing_config.processing_mode

    if orientation is not None:
        current_orientation = orientation
    if processing_mode is not None:
        current_processing_mode = processing_mode

    interpolation = INTERPOLATION_MAP.get(interpolation_name, cv2.INTER_LINEAR)
    target_width = matrix_config.width
    target_height = matrix_config.height

    # Swap dimensions for portrait mode BEFORE processing
    # This ensures the rotated result matches the physical display size
    if current_orientation == "portrait":
        target_width, target_height = target_height, target_width

    # Apply processing mode
    if current_processing_mode == "fit":
        processed = _resize_letterbox(frame, target_width, target_height, interpolation)
    elif current_processing_mode == "stretch":
        processed = cv2.resize(frame, (target_width, target_height), interpolation=interpolation)
    else:  # "center" (default)
        processed = _resize_center_crop(frame, target_width, target_height, interpolation)

    # Apply orientation (rotation for portrait)
    if current_orientation == "portrait":
        # For portrait, rotate 90° clockwise
        processed = cv2.rotate(processed, cv2.ROTATE_90_CLOCKWISE)

    return np.asarray(processed, dtype=np.uint8)


def _resize_center_crop(
    frame: NDArray[np.uint8],
    target_width: int,
    target_height: int,
    interpolation: int,
) -> NDArray[np.uint8]:
    """Crop to target aspect ratio from center."""
    h, w = frame.shape[:2]

    # Calculate target aspect ratio
    target_aspect = target_width / target_height
    current_aspect = w / h

    if current_aspect > target_aspect:
        # Image is wider than target, crop width (left and right)
        new_w = int(h * target_aspect)
        start_x = (w - new_w) // 2
        cropped = frame[0:h, start_x : start_x + new_w]
    else:
        # Image is taller than target, crop height (top and bottom)
        new_h = int(w / target_aspect)
        start_y = (h - new_h) // 2
        cropped = frame[start_y : start_y + new_h, 0:w]

    # Resize to matrix dimensions
    return cv2.resize(cropped, (target_width, target_height), interpolation=interpolation).astype(np.uint8)


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
