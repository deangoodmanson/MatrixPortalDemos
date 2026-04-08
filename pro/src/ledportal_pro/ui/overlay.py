"""Overlay drawing functionality."""

import math
from enum import Enum

import cv2
import numpy as np
from numpy.typing import NDArray

from ..config import MatrixConfig


class PreviewAlgorithm(Enum):
    """LED preview render algorithms, cycled with the 'o' key.

    Controls how each LED pixel is drawn in the right-hand preview pane.
    """

    SQUARES = 0
    CIRCLES = 1
    GAUSSIAN_RAW = 2
    GAUSSIAN_DIFFUSED = 3


LED_SIZE_STEPS: list[int] = [25, 50, 75, 100, 125, 150]
LED_SIZE_DEFAULT: int = 100

# Algorithm descriptions shown in console output
_ALGORITHM_LABELS: dict[PreviewAlgorithm, str] = {
    PreviewAlgorithm.SQUARES: "squares",
    PreviewAlgorithm.CIRCLES: "circles (hard edge, size adjustable with +/-)",
    PreviewAlgorithm.GAUSSIAN_RAW: "raw panel emulation (gaussian, sigma≈18% cell)",
    PreviewAlgorithm.GAUSSIAN_DIFFUSED: "diffused panel emulation (gaussian, sigma≈27% cell)",
}

# Gamma LUT: expand sRGB-encoded values to approximate LED matrix perceptual brightness.
# The LED matrix drives each LED with near-linear current, while a monitor applies
# sRGB gamma (≈2.2). Applying the inverse gamma to the preview makes it match the
# physical panel's perceived brightness. Built once at import time.
_GAMMA: float = 2.2
_GAMMA_LUT: NDArray[np.uint8] = np.array(
    [round(255 * (i / 255) ** (1.0 / _GAMMA)) if i > 0 else 0 for i in range(256)],
    dtype=np.uint8,
)

# Cache for vectorized distance grids keyed by (out_h, out_w, scale)
_dist_cache: dict[tuple[int, int, int], NDArray[np.float32]] = {}


def _get_dist_grid(out_h: int, out_w: int, scale: int) -> NDArray[np.float32]:
    """Return (and cache) a per-pixel distance-to-cell-centre array.

    For a given output size and scale factor this array is constant across
    all frames, so it is computed once and reused.

    Each value is the Euclidean distance from that output pixel to the centre
    of the LED cell it belongs to, based purely on the pixel's position within
    its cell (i.e. values repeat with period *scale* in both axes).

    Args:
        out_h: Output image height in pixels.
        out_w: Output image width in pixels.
        scale: Pixels per LED cell.

    Returns:
        Float32 array of shape (out_h, out_w).
    """
    key = (out_h, out_w, scale)
    if key not in _dist_cache:
        xs = (np.arange(out_w) % scale - scale // 2).astype(np.float32)
        ys = (np.arange(out_h) % scale - scale // 2).astype(np.float32)
        dx, dy = np.meshgrid(xs, ys)
        _dist_cache[key] = np.sqrt(dx**2 + dy**2)
    return _dist_cache[key]


def _render_painter(
    small_frame: NDArray[np.uint8],
    out_h: int,
    out_w: int,
    scale: int,
    radius: float,
    bg_color: tuple[int, int, int],
) -> NDArray[np.uint8]:
    """Render overlapping LED circles using painter's algorithm.

    Each LED is drawn as a filled circle in row-major order (top-left to
    bottom-right). Where adjacent circles overlap, the later circle's colour
    wins — the same way a painter's brush stroke covers what came before.

    math.ceil on radius ensures irrational values (e.g. 5√2 ≈ 7.07) produce
    an integer radius that genuinely reaches the target geometry without
    leaving tiny background gaps at corner intersection points.

    Args:
        small_frame: Matrix-sized BGR source frame.
        out_h: Output image height in pixels.
        out_w: Output image width in pixels.
        scale: Pixels per LED cell.
        radius: Geometric circle radius in pixels (may be non-integer).
        bg_color: BGR background colour.

    Returns:
        Upscaled BGR image with painter's-order circles.
    """
    h, w = small_frame.shape[:2]
    output = np.empty((out_h, out_w, 3), dtype=np.uint8)
    output[...] = bg_color
    r_int = math.ceil(radius)
    for row in range(h):
        for col in range(w):
            cx = col * scale + scale // 2
            cy = row * scale + scale // 2
            color = tuple(int(v) for v in small_frame[row, col])
            cv2.circle(output, (cx, cy), r_int, color, thickness=-1)
    return output


def _render_gaussian(
    small_frame: NDArray[np.uint8],
    out_h: int,
    out_w: int,
    scale: int,
    sigma: float,
) -> NDArray[np.uint8]:
    """Render LED matrix as Gaussian point-source blobs (diffuser simulation).

    Each LED is modelled as a single bright pixel at its cell centre.  A
    Gaussian blur spreads that point source across the panel, simulating the
    soft-focus effect of a physical diffuser panel placed in front of the LEDs.

    Contributions from adjacent LEDs blend additively, naturally producing the
    dark gaps between blobs and the soft halos around each LED — matching the
    appearance measured from a real diffused LED panel.

    Measured diffuser properties that drive the default sigma choice:
    - Cell pitch ≈ 139 px, gap-to-peak brightness ratio ≈ 37%
    - FWHM ≈ 63% of cell → σ = FWHM / 2.355 ≈ 0.27 × scale

    The output is normalised so that each blob's peak equals the original LED
    colour (peak_factor = 2π σ², the continuous 2-D Gaussian normalisation).

    Args:
        small_frame: Matrix-sized BGR source frame.
        out_h: Output image height in pixels.
        out_w: Output image width in pixels.
        scale: Pixels per LED cell.
        sigma: Gaussian standard deviation in output pixels.

    Returns:
        Upscaled BGR image with Gaussian-blurred LED blobs.
    """
    h, w = small_frame.shape[:2]

    # Place each LED as a single bright pixel at its cell centre
    dots = np.zeros((out_h, out_w, 3), dtype=np.float32)
    cy = np.arange(h) * scale + scale // 2
    cx = np.arange(w) * scale + scale // 2
    dots[np.ix_(cy, cx)] = small_frame.astype(np.float32)

    # Spread each point source with Gaussian blur (simulates the diffuser)
    blurred = cv2.GaussianBlur(dots, (0, 0), sigma)

    # Normalise: a 2-D Gaussian integrates to 1/(2π σ²) at the peak for a
    # unit-energy point source — multiply back to restore original brightness.
    peak_factor = 2.0 * math.pi * sigma * sigma
    return np.clip(blurred * peak_factor, 0, 255).astype(np.uint8)


def render_led_preview(
    small_frame: NDArray[np.uint8],
    algorithm: PreviewAlgorithm,
    led_size_pct: int,
    scale: int = 10,
    bg_color: tuple[int, int, int] = (0, 0, 0),
) -> NDArray[np.uint8]:
    """Render a matrix-sized LED frame as an upscaled preview image.

    Each LED pixel is drawn as a square, circle, or Gaussian blob depending
    on *algorithm*.  The output is always ``frame.height * scale`` ×
    ``frame.width * scale`` pixels in BGR format.

    For CIRCLES, *led_size_pct* controls the circle diameter as a percentage
    of the cell size.  Sizes ≤ 100% use a fast vectorised mask; sizes > 100%
    use painter's algorithm so overlapping circles render correctly.

    For SQUARES and Gaussian algorithms *led_size_pct* is ignored.

    Args:
        small_frame: Processed matrix-sized BGR frame (e.g. 64×32).
        algorithm: How to render each LED cell.
        led_size_pct: Circle diameter as percentage of cell (only for CIRCLES).
        scale: Pixels per LED cell. Default 10 → 64×32 becomes 640×320.
        bg_color: BGR background colour for non-LED pixels (circle modes only).

    Returns:
        Upscaled BGR image suitable for display.
    """
    h, w = small_frame.shape[:2]
    out_h, out_w = h * scale, w * scale

    if algorithm == PreviewAlgorithm.SQUARES:
        return cv2.resize(small_frame, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    if algorithm == PreviewAlgorithm.GAUSSIAN_RAW:
        sigma = scale * 0.18  # σ ≈ 18% of cell — calibrated to raw hardware, no diffuser
        return _render_gaussian(small_frame, out_h, out_w, scale, sigma)

    if algorithm == PreviewAlgorithm.GAUSSIAN_DIFFUSED:
        sigma = scale * 0.27  # σ ≈ 27% of cell — calibrated with diffuser panel
        return _render_gaussian(small_frame, out_h, out_w, scale, sigma)

    # CIRCLES — compute radius from led_size_pct
    half = scale / 2.0
    radius = scale * (led_size_pct / 200.0)

    if radius > half:
        # Overlapping circles — painter's algorithm (last-drawn-wins)
        return _render_painter(small_frame, out_h, out_w, scale, radius, bg_color)

    # Vectorised mask for non-overlapping circles (radius ≤ half-cell).
    colored = cv2.resize(small_frame, (out_w, out_h), interpolation=cv2.INTER_NEAREST)
    dist = _get_dist_grid(out_h, out_w, scale)
    mask = dist <= radius
    bg = np.empty((out_h, out_w, 3), dtype=np.uint8)
    bg[...] = bg_color
    return np.where(mask[:, :, np.newaxis], colored, bg).astype(np.uint8)


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
    algorithm: PreviewAlgorithm = PreviewAlgorithm.SQUARES,
    led_size_pct: int = LED_SIZE_DEFAULT,
    max_brightness: int = 255,
    demo_label: str = "",
) -> None:
    """Display a side-by-side preview window: camera feed on the left, enlarged
    matrix view on the right.

    A blue rectangle on the camera side shows exactly which region of the camera
    frame is sent to the matrix portal, accounting for both zoom and processing
    mode.  The camera side always shows the full unzoomed frame so the border
    visibly shrinks as zoom increases.

    In portrait mode the matrix view is rotated 90° CCW to match the physical
    display orientation.

    The LED pane is gamma-corrected to approximate the physical panel's perceived
    brightness: the matrix drives LEDs with near-linear current while a monitor
    applies sRGB gamma, making the preview appear darker than the real panel.
    If *max_brightness* is below 255 the LED pane is also scaled down accordingly.

    Args:
        original_frame: Full-resolution camera frame (pre-zoom).
        small_frame: Processed matrix-sized frame (before brightness limiting).
        matrix_config: Matrix configuration (used for scale factor).
        orientation: Current display orientation ("landscape" or "portrait").
        processing_mode: Current processing mode ("center", "stretch", or "fit").
        zoom_level: Current zoom level (1.0 = full frame, 0.5 = centre 50%).
        algorithm: How to render each LED cell in the matrix pane.
        led_size_pct: Circle diameter as percentage of cell (only for CIRCLES).
        max_brightness: LED matrix brightness cap (0-255); scales the LED pane.
        demo_label: Optional demo mode label to draw in red on the camera pane.
    """
    scale = 10

    # Enlarge the matrix view using the selected LED render algorithm
    enlarged = render_led_preview(small_frame, algorithm, led_size_pct, scale, bg_color=(0, 0, 0))

    # Scale down if the LED matrix is running below full brightness
    if max_brightness < 255:
        enlarged = np.clip(enlarged.astype(np.float32) * (max_brightness / 255), 0, 255).astype(
            np.uint8
        )

    # Apply gamma expansion so the preview matches physical LED matrix brightness.
    # LEDs emit near-linearly; a monitor applies sRGB gamma — this corrects for that.
    enlarged = cv2.LUT(enlarged, _GAMMA_LUT)

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

    # Draw demo label in red on the camera pane (bottom-left)
    if demo_label:
        cam_h_resized = cam_resized.shape[0]
        cv2.putText(
            cam_resized,
            demo_label,
            (10, cam_h_resized - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    combined = np.hstack([cam_resized, enlarged])
    cv2.imshow(
        "[ Camera ] | [ LED Matrix Preview ]    Note: The console must have window focus for keyboard commands.",
        combined,
    )
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
