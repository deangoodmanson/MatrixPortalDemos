"""Overlay drawing functionality."""

import math
import cv2
import numpy as np
from enum import Enum
from numpy.typing import NDArray

from ..config import MatrixConfig


class PreviewMode(Enum):
    """LED preview render modes, cycled with the 'o' key.

    Circle sizes are expressed as a percentage of the LED cell diameter.
    Modes ≤ 100% use a fast vectorised mask; modes > 100% use painter's
    algorithm so that overlapping circles from adjacent LEDs are drawn correctly.

    Controls how each LED pixel is drawn in the right-hand preview pane.
    """

    SQUARES = 0              # Plain nearest-neighbour upscale (current default)
    CIRCLES_50 = 1           # 50%  — wide gaps between circles
    CIRCLES_75 = 2           # 75%  — clear gaps between circles
    CIRCLES_100 = 3          # 100% — circle exactly fills the cell (edge-to-edge)
    CIRCLES_125 = 4          # 125% — circles overlap neighbouring cells slightly
    CIRCLES_CORNER = 5       # ~141% — corner-touch; painter's algorithm (last drawn wins)
    CIRCLES_CORNER_BLEND = 6 # ~141% — corner-touch; weighted-average colour blending


# Mode descriptions shown in console output
_MODE_LABELS: dict[PreviewMode, str] = {
    PreviewMode.SQUARES: "squares",
    PreviewMode.CIRCLES_50: "circles 50% (wide gaps)",
    PreviewMode.CIRCLES_75: "circles 75% (gapped)",
    PreviewMode.CIRCLES_100: "circles 100% (edge-to-edge)",
    PreviewMode.CIRCLES_125: "circles 125% (slight overlap)",
    PreviewMode.CIRCLES_CORNER: "circles ~141% corner-touch (painter's)",
    PreviewMode.CIRCLES_CORNER_BLEND: "circles ~141% corner-touch (blended)",
}

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
        _dist_cache[key] = np.sqrt(dx ** 2 + dy ** 2)
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


def _render_blend(
    small_frame: NDArray[np.uint8],
    out_h: int,
    out_w: int,
    scale: int,
    radius: float,
    bg_color: tuple[int, int, int],
) -> NDArray[np.uint8]:
    """Render overlapping LED circles with weighted-average colour blending.

    Instead of last-drawn-wins, every pixel receives the weighted average of
    all LED circles that cover it. This produces smooth colour gradients in the
    lens-shaped overlap zones between adjacent LEDs rather than a hard boundary
    determined by draw order.

    Algorithm:
    1. Pre-build a boolean circle mask of shape (2r+1, 2r+1) shared by all LEDs.
    2. For each LED, add its colour * mask to a float accumulator and increment
       a coverage counter for each covered pixel (bounding-box slice, O(r²) work).
    3. Divide accumulator by counter where coverage > 0; fill with bg_color elsewhere.

    Args:
        small_frame: Matrix-sized BGR source frame.
        out_h: Output image height in pixels.
        out_w: Output image width in pixels.
        scale: Pixels per LED cell.
        radius: Geometric circle radius in pixels (may be non-integer).
        bg_color: BGR background colour.

    Returns:
        Upscaled BGR image with blended circles.
    """
    h, w = small_frame.shape[:2]
    r_int = math.ceil(radius)

    # Pre-build a shared circle mask — same geometry for every LED
    mask_size = 2 * r_int + 1
    local_ys = np.arange(mask_size, dtype=np.float32) - r_int
    local_xs = np.arange(mask_size, dtype=np.float32) - r_int
    ldx, ldy = np.meshgrid(local_xs, local_ys)
    circle_mask = (np.sqrt(ldx ** 2 + ldy ** 2) <= radius).astype(np.float32)

    accumulator = np.zeros((out_h, out_w, 3), dtype=np.float32)
    count = np.zeros((out_h, out_w), dtype=np.float32)

    for row in range(h):
        for col in range(w):
            cx = col * scale + scale // 2
            cy = row * scale + scale // 2

            # Bounding box in output image coords, clipped to image bounds
            ox1, oy1 = cx - r_int, cy - r_int
            x1 = max(0, ox1)
            y1 = max(0, oy1)
            x2 = min(out_w, cx + r_int + 1)
            y2 = min(out_h, cy + r_int + 1)

            # Corresponding slice of the pre-built mask
            mx1, my1 = x1 - ox1, y1 - oy1
            local_mask = circle_mask[my1: my1 + (y2 - y1), mx1: mx1 + (x2 - x1)]

            color = small_frame[row, col].astype(np.float32)
            accumulator[y1:y2, x1:x2] += local_mask[:, :, np.newaxis] * color
            count[y1:y2, x1:x2] += local_mask

    # Weighted average where covered; background colour elsewhere
    bg = np.array(bg_color, dtype=np.float32)
    result = np.where(
        count[:, :, np.newaxis] > 0,
        accumulator / np.maximum(count[:, :, np.newaxis], 1.0),
        bg,
    )
    return np.clip(result, 0, 255).astype(np.uint8)


def render_led_preview(
    small_frame: NDArray[np.uint8],
    mode: PreviewMode = PreviewMode.SQUARES,
    scale: int = 10,
    bg_color: tuple[int, int, int] = (0, 0, 0),
) -> NDArray[np.uint8]:
    """Render a matrix-sized LED frame as an upscaled preview image.

    Each LED pixel is drawn as a square or circle depending on *mode*.
    The output is always ``frame.height * scale`` × ``frame.width * scale``
    pixels in BGR format.

    Modes ≤ 100% (circles fit within their cell) use a fast vectorised NumPy
    mask.  Modes > 100% (circles extend into adjacent cells) are dispatched to
    either ``_render_painter`` (last-drawn-wins) or ``_render_blend``
    (weighted-average colour blending in overlap zones).

    Args:
        small_frame: Processed matrix-sized BGR frame (e.g. 64×32).
        mode: How to render each LED cell.
        scale: Pixels per LED cell. Default 10 → 64×32 becomes 640×320.
        bg_color: BGR background colour for non-LED pixels (circle modes only).

    Returns:
        Upscaled BGR image suitable for display.
    """
    h, w = small_frame.shape[:2]
    out_h, out_w = h * scale, w * scale

    if mode == PreviewMode.SQUARES:
        return cv2.resize(small_frame, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    # Radius as a fraction of cell size (diameter = scale × pct / 100)
    half = scale / 2.0
    if mode == PreviewMode.CIRCLES_50:
        radius = scale * 0.25       # 2.5px — 50% diameter, wide gaps
    elif mode == PreviewMode.CIRCLES_75:
        radius = scale * 0.375      # 3.75px — 75% diameter, clear gaps
    elif mode == PreviewMode.CIRCLES_100:
        radius = half               # 5.0px — 100% diameter, tangent to edges
    elif mode == PreviewMode.CIRCLES_125:
        radius = scale * 0.625      # 6.25px — 125% diameter, slight overlap
    else:  # CIRCLES_CORNER and CIRCLES_CORNER_BLEND — same geometry
        radius = half * (2 ** 0.5)  # 5√2 ≈ 7.07px — ~141%, passes through corners

    if radius > half:
        if mode == PreviewMode.CIRCLES_CORNER_BLEND:
            return _render_blend(small_frame, out_h, out_w, scale, radius, bg_color)
        return _render_painter(small_frame, out_h, out_w, scale, radius, bg_color)

    # Vectorised mask for non-overlapping modes (radius ≤ half-cell).
    # 1. Upscale with nearest-neighbour so each pixel carries its LED colour.
    # 2. Build a boolean mask: True where pixel is within radius of cell centre.
    # 3. Replace masked-out pixels with bg_color.
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
    render_mode: PreviewMode = PreviewMode.SQUARES,
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
        render_mode: How to render each LED cell in the matrix pane.
    """
    scale = 10

    # Enlarge the matrix view using the selected LED render mode
    enlarged = render_led_preview(small_frame, render_mode, scale)

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
