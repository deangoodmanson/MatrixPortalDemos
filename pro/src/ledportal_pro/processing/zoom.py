"""Zoom crop processing for camera frames."""

import numpy as np
from numpy.typing import NDArray


def apply_zoom_crop(frame: NDArray[np.uint8], zoom_percentage: float) -> NDArray[np.uint8]:
    """Crop frame to centered percentage (zoom effect).

    Args:
        frame: Input BGR image
        zoom_percentage: Percentage of frame to keep (0.25-1.0)
                        1.0 = no crop (100%), 0.5 = center 50% (2x zoom)

    Returns:
        Cropped frame centered on original
    """
    # No-op optimization for 100% zoom
    if zoom_percentage >= 1.0:
        return frame

    h, w = frame.shape[:2]

    # Calculate crop dimensions
    new_w = int(w * zoom_percentage)
    new_h = int(h * zoom_percentage)

    # Calculate center offsets
    start_x = (w - new_w) // 2
    start_y = (h - new_h) // 2

    # Return cropped frame
    return frame[start_y : start_y + new_h, start_x : start_x + new_w]
