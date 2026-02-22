"""Overlay drawing functionality."""

from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from ..config import MatrixConfig


def draw_countdown_overlay(
    frame: NDArray[np.uint8],
    number: int,
    matrix_config: MatrixConfig,
    color: tuple[int, int, int] = (0, 0, 255),
    orientation: str = "landscape",
) -> NDArray[np.uint8]:
    """Draw countdown number overlay on frame.

    Args:
        frame: BGR image as numpy array (will be copied).
        number: Number to display (3, 2, 1).
        matrix_config: Matrix configuration for positioning.
        color: BGR color for the text.
        orientation: Display orientation ("landscape" or "portrait").

    Returns:
        New frame with countdown overlay.
    """
    overlay = frame.copy()

    if orientation == "portrait":
        # For portrait mode (frame is already rotated 90° CW)
        # Draw text rotated 90° CW so it appears upright
        # Position in lower right (which was lower left before rotation)
        text = str(number)

        # Create a rotated text image
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]

        # Create temporary canvas for text
        temp = np.zeros((text_size[1] + 10, text_size[0] + 10, 3), dtype=np.uint8)
        cv2.putText(
            temp,
            text,
            (5, text_size[1] + 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )

        # Rotate text 90° clockwise
        rotated_text = cv2.rotate(temp, cv2.ROTATE_90_CLOCKWISE)

        # Position in lower right corner
        h, w = rotated_text.shape[:2]
        y_start = matrix_config.height - h - 2
        x_start = matrix_config.width - w - 2

        # Overlay the rotated text (only non-black pixels)
        mask = np.any(rotated_text > 0, axis=2)
        overlay[y_start : y_start + h, x_start : x_start + w][mask] = rotated_text[mask]
    else:
        # Landscape mode - position in lower left corner
        position = (2, matrix_config.height - 4)
        cv2.putText(
            overlay,
            str(number),
            position,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )

    return overlay


def draw_text_overlay(
    frame: NDArray[np.uint8],
    text: str,
    position: tuple[int, int],
    color: tuple[int, int, int] = (255, 255, 255),
    font_scale: float = 0.5,
    thickness: int = 1,
) -> NDArray[np.uint8]:
    """Draw text overlay on frame.

    Args:
        frame: BGR image as numpy array (will be copied).
        text: Text to display.
        position: (x, y) position for text.
        color: BGR color for the text.
        font_scale: Font size scale.
        thickness: Text thickness.

    Returns:
        New frame with text overlay.
    """
    overlay = frame.copy()

    cv2.putText(
        overlay,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA,
    )

    return overlay


def draw_mode_indicator(
    frame: NDArray[np.uint8],
    mode_text: str,
    matrix_config: MatrixConfig,
) -> NDArray[np.uint8]:
    """Draw mode indicator in corner of frame.

    Args:
        frame: BGR image as numpy array (will be copied).
        mode_text: Short text indicating current mode (e.g., "B&W").
        matrix_config: Matrix configuration for positioning.

    Returns:
        New frame with mode indicator.
    """
    overlay = frame.copy()

    # Position in upper right corner
    text_size = cv2.getTextSize(mode_text, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)[0]
    position = (matrix_config.width - text_size[0] - 2, 8)

    cv2.putText(
        overlay,
        mode_text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.3,
        (0, 255, 255),  # Yellow
        1,
        cv2.LINE_AA,
    )

    return overlay


def draw_border(
    frame: NDArray[np.uint8],
    color: tuple[int, int, int] = (255, 0, 0),
) -> NDArray[np.uint8]:
    """Draw single-pixel border around frame.

    Args:
        frame: BGR image as numpy array (will be copied).
        color: BGR color for the border.

    Returns:
        New frame with border.
    """
    bordered = frame.copy()
    height, width = bordered.shape[:2]

    # Draw 1-pixel border around all edges
    bordered[0, :] = color  # Top edge
    bordered[height - 1, :] = color  # Bottom edge
    bordered[:, 0] = color  # Left edge
    bordered[:, width - 1] = color  # Right edge

    return bordered
