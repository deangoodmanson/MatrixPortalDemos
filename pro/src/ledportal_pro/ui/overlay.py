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
) -> NDArray[np.uint8]:
    """Draw countdown number overlay on frame.

    Args:
        frame: BGR image as numpy array (will be copied).
        number: Number to display (3, 2, 1).
        matrix_config: Matrix configuration for positioning.
        color: BGR color for the text.

    Returns:
        New frame with countdown overlay.
    """
    overlay = frame.copy()

    # Position in lower left corner
    position = (2, matrix_config.height - 4)

    cv2.putText(
        overlay,
        str(number),
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,  # Font scale
        color,
        2,  # Thickness
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
