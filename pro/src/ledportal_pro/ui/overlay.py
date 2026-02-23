"""Overlay drawing functionality."""

import cv2
import numpy as np
from numpy.typing import NDArray

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


def show_preview(
    original_frame: NDArray[np.uint8],
    small_frame: NDArray[np.uint8],
    matrix_config: MatrixConfig,
    orientation: str = "landscape",
    processing_mode: str = "center",
    zoom_level: float = 1.0,
) -> None:
    """Display a side-by-side preview window: camera feed on the left, enlarged
    matrix view on the right.

    A blue rectangle on the camera side shows exactly which region of the camera
    frame is sent to the matrix portal, accounting for both zoom and processing
    mode.  The camera side always shows the full unzoomed frame so the border
    visibly shrinks as zoom increases.

    In portrait mode the matrix view is rotated 90° CCW to match the physical
    display orientation.

    Args:
        original_frame: Full-resolution camera frame (pre-zoom).
        small_frame: Processed matrix-sized frame.
        matrix_config: Matrix configuration (used for scale factor).
        orientation: Current display orientation ("landscape" or "portrait").
        processing_mode: Current processing mode ("center", "stretch", or "fit").
        zoom_level: Current zoom level (1.0 = full frame, 0.5 = centre 50%).
    """
    scale = 10

    # Enlarge the matrix view (nearest-neighbour for crisp pixels)
    enlarged = cv2.resize(
        small_frame,
        (matrix_config.width * scale, matrix_config.height * scale),
        interpolation=cv2.INTER_NEAREST,
    )

    # In portrait mode rotate to match the physical display
    if orientation == "portrait":
        enlarged = cv2.rotate(enlarged, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # Scale camera frame to match enlarged matrix view height
    target_height = enlarged.shape[0]
    cam_h, cam_w = original_frame.shape[:2]
    cam_resized = cv2.resize(original_frame, (int(cam_w * target_height / cam_h), target_height))

    # --- Compute the effective capture region in original camera coordinates ---
    # Step 1: zoom crop (shrinks from centre)
    if zoom_level < 1.0:
        zoom_w = int(cam_w * zoom_level)
        zoom_h = int(cam_h * zoom_level)
        zoom_x1 = (cam_w - zoom_w) // 2
        zoom_y1 = (cam_h - zoom_h) // 2
    else:
        zoom_w, zoom_h = cam_w, cam_h
        zoom_x1, zoom_y1 = 0, 0

    # Step 2: processing crop within the zoomed region
    if processing_mode == "center":
        # Target dims before rotation (portrait swaps w/h before cropping)
        tw = matrix_config.height if orientation == "portrait" else matrix_config.width
        th = matrix_config.width if orientation == "portrait" else matrix_config.height
        target_aspect = tw / th
        zoom_aspect = zoom_w / zoom_h
        if zoom_aspect > target_aspect:
            inner_w = int(zoom_h * target_aspect)
            inner_x1 = (zoom_w - inner_w) // 2
            x1, y1 = zoom_x1 + inner_x1, zoom_y1
            x2, y2 = x1 + inner_w, zoom_y1 + zoom_h
        else:
            inner_h = int(zoom_w / target_aspect)
            inner_y1 = (zoom_h - inner_h) // 2
            x1, y1 = zoom_x1, zoom_y1 + inner_y1
            x2, y2 = zoom_x1 + zoom_w, y1 + inner_h
    else:
        # stretch / fit — full zoomed area is used
        x1, y1 = zoom_x1, zoom_y1
        x2, y2 = zoom_x1 + zoom_w, zoom_y1 + zoom_h

    # Scale rect from original camera coordinates to preview coordinates
    s = target_height / cam_h
    px1, py1 = int(x1 * s), int(y1 * s)
    px2, py2 = min(int(x2 * s), cam_resized.shape[1]) - 1, int(y2 * s) - 1
    cv2.rectangle(cam_resized, (px1, py1), (px2, py2), (255, 0, 0), 1)

    combined = np.hstack([cam_resized, enlarged])
    cv2.imshow("Camera | LED Matrix (10x)", combined)
    cv2.waitKey(1)


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
