"""Snapshot processing utilities for LED Portal.

This module provides functions to convert and upscale LED matrix snapshot images
for better viewing and sharing.
"""

import math
from enum import Enum
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


class LedMode(Enum):
    """LED preview render modes for snapshot export.

    Matches the PreviewMode enum in the pro version. Circle sizes are expressed
    as a percentage of the LED cell diameter (cell = scale × scale pixels).

    Modes ≤ 100% use a fast vectorised NumPy mask (no inter-cell overlap).
    Modes > 100% use painter's algorithm (PIL ellipses, last-drawn wins) or
    weighted-average colour blending in overlap zones.
    """

    SQUARES = 0  # Plain nearest-neighbour upscale
    CIRCLES_50 = 1  # 50%  — wide gaps between circles
    CIRCLES_75 = 2  # 75%  — clear gaps between circles
    CIRCLES_100 = 3  # 100% — circle exactly fills the cell (edge-to-edge)
    CIRCLES_125 = 4  # 125% — circles overlap neighbouring cells slightly
    CIRCLES_CORNER = 5  # ~141% — corner-touch; painter's algorithm (last drawn wins)
    CIRCLES_CORNER_BLEND = 6  # ~141% — corner-touch; weighted-average colour blending
    GAUSSIAN = 7  # Gaussian diffuser simulation — σ ≈ 27% of cell (matches real panel)


def _render_painter_pil(
    pixels: np.ndarray,
    out_h: int,
    out_w: int,
    scale: int,
    radius: float,
    background_color: tuple[int, int, int],
) -> np.ndarray:
    """Render overlapping LED circles using painter's algorithm (PIL).

    Draws each LED as a filled ellipse in row-major order. Where adjacent
    circles overlap, the later circle's colour wins — the same way a painter's
    brush stroke covers what came before.

    math.ceil on radius ensures irrational values (e.g. 5√2 ≈ 7.07) produce
    an integer radius that genuinely reaches the target geometry without leaving
    tiny background gaps at corner intersection points.

    Args:
        pixels: Input RGB image as numpy array of shape (H, W, 3).
        out_h: Output image height in pixels.
        out_w: Output image width in pixels.
        scale: Pixels per LED cell.
        radius: Geometric circle radius in pixels (may be non-integer).
        background_color: RGB background colour.

    Returns:
        Upscaled RGB image as numpy array.
    """
    h, w = pixels.shape[:2]
    r_int = math.ceil(radius)
    output = Image.new("RGB", (out_w, out_h), background_color)
    draw = ImageDraw.Draw(output)
    for row in range(h):
        for col in range(w):
            cx = col * scale + scale // 2
            cy = row * scale + scale // 2
            color = tuple(int(v) for v in pixels[row, col])
            draw.ellipse((cx - r_int, cy - r_int, cx + r_int, cy + r_int), fill=color)
    return np.array(output)


def _render_blend_pil(
    pixels: np.ndarray,
    out_h: int,
    out_w: int,
    scale: int,
    radius: float,
    background_color: tuple[int, int, int],
) -> np.ndarray:
    """Render overlapping LED circles with weighted-average colour blending.

    Instead of last-drawn-wins, every output pixel receives the weighted average
    of all LED circles that cover it. This produces smooth colour gradients in
    the lens-shaped overlap zones between adjacent LEDs.

    Algorithm:
    1. Pre-build a boolean circle mask of shape (2r+1, 2r+1) shared by all LEDs.
    2. For each LED, add its colour × mask to a float accumulator and increment
       a coverage counter (bounding-box slice per LED, O(r²) work each).
    3. Divide accumulator by counter where coverage > 0; fill with background elsewhere.

    Args:
        pixels: Input RGB image as numpy array of shape (H, W, 3).
        out_h: Output image height in pixels.
        out_w: Output image width in pixels.
        scale: Pixels per LED cell.
        radius: Geometric circle radius in pixels (may be non-integer).
        background_color: RGB background colour.

    Returns:
        Upscaled RGB image as numpy array with blended overlap zones.
    """
    h, w = pixels.shape[:2]
    r_int = math.ceil(radius)

    # Pre-build a shared circle mask — same geometry for every LED
    mask_size = 2 * r_int + 1
    local_ys = np.arange(mask_size, dtype=np.float32) - r_int
    local_xs = np.arange(mask_size, dtype=np.float32) - r_int
    ldx, ldy = np.meshgrid(local_xs, local_ys)
    circle_mask = (np.sqrt(ldx**2 + ldy**2) <= radius).astype(np.float32)

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
            local_mask = circle_mask[my1 : my1 + (y2 - y1), mx1 : mx1 + (x2 - x1)]

            color = pixels[row, col].astype(np.float32)
            accumulator[y1:y2, x1:x2] += local_mask[:, :, np.newaxis] * color
            count[y1:y2, x1:x2] += local_mask

    # Weighted average where covered; background colour elsewhere
    bg = np.array(background_color, dtype=np.float32)
    result = np.where(
        count[:, :, np.newaxis] > 0,
        accumulator / np.maximum(count[:, :, np.newaxis], 1.0),
        bg,
    )
    return np.clip(result, 0, 255).astype(np.uint8)


def _render_gaussian_pil(
    pixels: np.ndarray,
    out_h: int,
    out_w: int,
    scale: int,
    sigma: float,
) -> np.ndarray:
    """Gaussian diffuser simulation using a Gaussian-weighted accumulator (PIL/NumPy).

    Equivalent to _render_blend_pil but with Gaussian weights instead of a
    uniform circle mask: each LED contributes its colour to surrounding pixels
    with a Gaussian falloff from its cell centre.  The peak weight is 1.0 so
    the LED centre pixel retains the original brightness; contributions from
    adjacent LEDs are negligible at the default sigma (< 0.1% at 1 cell away).

    Args:
        pixels: Input RGB image as numpy array of shape (H, W, 3).
        out_h: Output image height in pixels.
        out_w: Output image width in pixels.
        scale: Pixels per LED cell.
        sigma: Gaussian standard deviation in output pixels.

    Returns:
        Upscaled RGB image as numpy array with Gaussian-blurred LED blobs.
    """
    h, w = pixels.shape[:2]
    r = math.ceil(3 * sigma)  # cut off at 3σ — beyond this the weight is < 0.01%

    # Pre-build the Gaussian kernel (peak = 1.0, falls off as Gaussian)
    local_ys = np.arange(2 * r + 1, dtype=np.float32) - r
    local_xs = np.arange(2 * r + 1, dtype=np.float32) - r
    ldx, ldy = np.meshgrid(local_xs, local_ys)
    gauss_kernel = np.exp(-(ldx**2 + ldy**2) / (2 * sigma**2)).astype(np.float32)

    accumulator = np.zeros((out_h, out_w, 3), dtype=np.float32)

    for row in range(h):
        for col in range(w):
            cx = col * scale + scale // 2
            cy = row * scale + scale // 2

            # Bounding box in output image coords, clipped to image bounds
            ox1, oy1 = cx - r, cy - r
            x1 = max(0, ox1)
            y1 = max(0, oy1)
            x2 = min(out_w, cx + r + 1)
            y2 = min(out_h, cy + r + 1)

            # Corresponding slice of the pre-built kernel
            mx1, my1 = x1 - ox1, y1 - oy1
            local_weights = gauss_kernel[my1 : my1 + (y2 - y1), mx1 : mx1 + (x2 - x1)]

            color = pixels[row, col].astype(np.float32)
            accumulator[y1:y2, x1:x2] += local_weights[:, :, np.newaxis] * color

    return np.clip(accumulator, 0, 255).astype(np.uint8)


def _render_led_array(
    pixels: np.ndarray,
    mode: LedMode,
    scale: int,
    background_color: tuple[int, int, int],
) -> np.ndarray:
    """Render an LED pixel array to an upscaled image array.

    Dispatches to the appropriate rendering algorithm based on mode:
    - SQUARES: PIL NEAREST resize (fast, no circles)
    - ≤100% circles: vectorised NumPy distance mask
    - >100% circles: painter's algorithm or weighted-average blending

    Args:
        pixels: Input RGB image as numpy array of shape (H, W, 3).
        mode: Render mode controlling circle size and algorithm.
        scale: Pixels per LED cell.
        background_color: RGB background colour (used in circle modes).

    Returns:
        Upscaled RGB image as numpy array of shape (H*scale, W*scale, 3).
    """
    h, w = pixels.shape[:2]
    out_h, out_w = h * scale, w * scale
    half = scale / 2.0

    if mode == LedMode.SQUARES:
        img = Image.fromarray(pixels.astype(np.uint8), "RGB")
        return np.array(img.resize((out_w, out_h), Image.Resampling.NEAREST))

    if mode == LedMode.GAUSSIAN:
        sigma = scale * 0.27  # σ ≈ 2.7 px @ scale=10 → FWHM ≈ 63% of cell
        return _render_gaussian_pil(pixels, out_h, out_w, scale, sigma)

    # Radius as a fraction of cell size (diameter = scale × pct / 100)
    if mode == LedMode.CIRCLES_50:
        radius = scale * 0.25  # 2.5px — 50% diameter, wide gaps
    elif mode == LedMode.CIRCLES_75:
        radius = scale * 0.375  # 3.75px — 75% diameter, clear gaps
    elif mode == LedMode.CIRCLES_100:
        radius = half  # 5.0px — 100% diameter, tangent to edges
    elif mode == LedMode.CIRCLES_125:
        radius = scale * 0.625  # 6.25px — 125% diameter, slight overlap
    else:  # CIRCLES_CORNER and CIRCLES_CORNER_BLEND — same geometry
        radius = half * (2**0.5)  # 5√2 ≈ 7.07px — ~141%, passes through corners

    if radius > half:
        if mode == LedMode.CIRCLES_CORNER_BLEND:
            return _render_blend_pil(pixels, out_h, out_w, scale, radius, background_color)
        return _render_painter_pil(pixels, out_h, out_w, scale, radius, background_color)

    # Vectorised mask for non-overlapping modes (radius ≤ half-cell).
    # 1. Upscale with nearest-neighbour so each pixel carries its LED colour.
    # 2. Build a boolean mask: True where pixel is within radius of cell centre.
    # 3. Replace masked-out pixels with background_color.
    img = Image.fromarray(pixels.astype(np.uint8), "RGB")
    upscaled = np.array(img.resize((out_w, out_h), Image.Resampling.NEAREST))
    xs = (np.arange(out_w) % scale - scale // 2).astype(np.float32)
    ys = (np.arange(out_h) % scale - scale // 2).astype(np.float32)
    dx, dy = np.meshgrid(xs, ys)
    dist = np.sqrt(dx**2 + dy**2)
    mask = dist <= radius
    bg = np.empty((out_h, out_w, 3), dtype=np.uint8)
    bg[...] = np.array(background_color, dtype=np.uint8)
    return np.where(mask[:, :, np.newaxis], upscaled, bg).astype(np.uint8)


def export_pdf(
    snapshot_path: str | Path,
    output_path: str | Path | None = None,
    original_path: str | Path | None = None,
    mode: LedMode = LedMode.SQUARES,
    scale_factor: int = 10,
    background_color: tuple[int, int, int] = (0, 0, 0),
    thumbnail_inches: float = 2.0,
    dpi: int = 300,
) -> Path:
    """Export snapshot as a US Letter PDF with LED preview, original image, and thumbnails.

    Composes a PDF on an 8.5″×11″ US Letter page containing four elements
    stacked vertically and centred:

    1. LED matrix preview — the snapshot rendered with the chosen LED mode
    2. Original camera capture (if provided) — scaled to fit page width
    3. Thumbnail — aspect-ratio-preserving blocky upscale (longest side = thumbnail_inches)
    4. Pixel-to-pixel — the raw snapshot at native resolution (e.g. 32×64 or 64×32)

    Args:
        snapshot_path: Path to the LED matrix snapshot file (BMP or PNG, typically 32×64 or 64×32).
        output_path: Path to output PDF file. If None, uses snapshot filename with .pdf extension.
        original_path: Optional path to the original camera capture image.
        mode: LED render mode for the preview section. Default is SQUARES.
        scale_factor: Pixels per LED cell for the preview. Default is 10.
        background_color: RGB background colour for non-LED areas in preview. Default black.
        thumbnail_inches: Physical size of the thumbnail's longest side in inches.
            The shorter side scales proportionally. Default is 2.0.
        dpi: Resolution in dots per inch. Controls physical print size. Default is 300.

    Returns:
        Path to the created PDF file.

    Example:
        >>> export_pdf("snapshot_20260314_120000.bmp")
        PosixPath('snapshot_20260314_120000.pdf')
    """
    snapshot_path = Path(snapshot_path)
    output_path = snapshot_path.with_suffix(".pdf") if output_path is None else Path(output_path)

    # US Letter page at target DPI
    page_w = round(8.5 * dpi)
    page_h = round(11.0 * dpi)
    margin = round(0.5 * dpi)
    padding = round(0.25 * dpi)
    content_w = page_w - 2 * margin

    # Load snapshot and render LED preview
    snapshot_img = Image.open(snapshot_path).convert("RGB")
    snapshot_pixels = np.array(snapshot_img)
    led_array = _render_led_array(snapshot_pixels, mode, scale_factor, background_color)
    led_img = Image.fromarray(led_array, "RGB")

    # Scale LED preview to fit content width
    if led_img.width > content_w:
        led_scale = content_w / led_img.width
        led_img = led_img.resize(
            (content_w, round(led_img.height * led_scale)), Image.Resampling.NEAREST
        )

    # Thumbnail: preserve aspect ratio, longest side = thumbnail_inches
    snap_w, snap_h = snapshot_img.size
    longest = max(snap_w, snap_h)
    thumb_scale = (thumbnail_inches * dpi) / longest
    thumb_w = round(snap_w * thumb_scale)
    thumb_h = round(snap_h * thumb_scale)
    thumb_img = snapshot_img.resize((thumb_w, thumb_h), Image.Resampling.NEAREST)

    # Pixel-to-pixel: raw snapshot at native resolution (no scaling)
    pixel_img = snapshot_img.copy()

    # Load original camera image if provided
    original_img = None
    if original_path is not None:
        original_img = Image.open(Path(original_path)).convert("RGB")
        # Scale original to fit content width
        orig_scale = content_w / original_img.width
        orig_h = round(original_img.height * orig_scale)
        original_img = original_img.resize((content_w, orig_h), Image.Resampling.LANCZOS)

    # Build US Letter canvas
    canvas = Image.new("RGB", (page_w, page_h), (255, 255, 255))

    y = margin

    # 1. LED preview (centred)
    x = margin + (content_w - led_img.width) // 2
    canvas.paste(led_img, (x, y))
    y += led_img.height + padding

    # 2. Original image (centred)
    if original_img is not None:
        x = margin + (content_w - original_img.width) // 2
        canvas.paste(original_img, (x, y))
        y += original_img.height + padding

    # 3. Thumbnail (centred)
    x = margin + (content_w - thumb_img.width) // 2
    canvas.paste(thumb_img, (x, y))
    y += thumb_img.height + padding

    # 4. Pixel-to-pixel (centred)
    x = margin + (content_w - pixel_img.width) // 2
    canvas.paste(pixel_img, (x, y))

    canvas.save(output_path, "PDF", resolution=dpi)

    return output_path


def export_png(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Export snapshot as PNG format.

    Args:
        input_path: Path to input BMP file.
        output_path: Path to output PNG file. If None, uses input filename with .png extension.

    Returns:
        Path to the created PNG file.

    Example:
        >>> export_png("snapshot_20260211_120000.bmp")
        PosixPath('snapshot_20260211_120000.png')
    """
    input_path = Path(input_path)
    output_path = input_path.with_suffix(".png") if output_path is None else Path(output_path)

    # Open and convert
    img = Image.open(input_path)
    img.save(output_path, "PNG")

    return output_path


def export_blocks(
    input_path: str | Path,
    output_path: str | Path | None = None,
    scale_factor: int = 10,
) -> Path:
    """Export snapshot with square block effect.

    Each original pixel becomes a scale_factor × scale_factor square block,
    creating a blocky display appearance.

    Args:
        input_path: Path to input image file (BMP or PNG).
        output_path: Path to output PNG file. If None, appends '_pixelated' to filename.
        scale_factor: Pixels per LED. Each original pixel becomes scale_factor × scale_factor.
            Default is 10 (64×32 becomes 640×320).

    Returns:
        Path to the created PNG file.

    Example:
        >>> export_blocks("snapshot.bmp", scale_factor=10)
        PosixPath('snapshot_blocks.png')
    """
    input_path = Path(input_path)
    output_path = (
        input_path.with_stem(f"{input_path.stem}_blocks").with_suffix(".png")
        if output_path is None
        else Path(output_path)
    )

    # Open image
    img = Image.open(input_path)

    # Calculate new size
    new_width = img.width * scale_factor
    new_height = img.height * scale_factor

    # Resize using NEAREST neighbor - this creates crisp square pixels
    upscaled = img.resize((new_width, new_height), Image.Resampling.NEAREST)

    # Save as PNG
    upscaled.save(output_path, "PNG")

    return output_path


def export_circles(
    input_path: str | Path,
    output_path: str | Path | None = None,
    scale_factor: int = 10,
    led_size_ratio: float = 0.9,
    background_color: tuple[int, int, int] = (0, 0, 0),
) -> Path:
    """Export snapshot with circular effect.

    Each original pixel becomes a circle on a black background, mimicking the
    appearance of a real LED matrix display.

    Args:
        input_path: Path to input image file (BMP or PNG).
        output_path: Path to output PNG file. If None, appends '_led' to filename.
        scale_factor: Pixels per LED. Each original pixel becomes a
            scale_factor × scale_factor cell. Default is 10.
        led_size_ratio: Circle size relative to cell size (0.0-1.0).
            0.9 means circles are 90% of cell size, leaving small gaps.
            Default is 0.9.
        background_color: RGB tuple for background. Default is black (0, 0, 0).

    Returns:
        Path to the created PNG file.

    Example:
        >>> export_circles("snapshot.bmp", scale_factor=10, led_size_ratio=0.9)
        PosixPath('snapshot_circles.png')
    """
    input_path = Path(input_path)
    output_path = (
        input_path.with_stem(f"{input_path.stem}_circles").with_suffix(".png")
        if output_path is None
        else Path(output_path)
    )

    # Open and convert to RGB if needed
    img = Image.open(input_path).convert("RGB")

    # Convert to numpy array for pixel access
    pixels = np.array(img)
    height, width = pixels.shape[:2]

    # Create output image
    new_width = width * scale_factor
    new_height = height * scale_factor
    output = Image.new("RGB", (new_width, new_height), background_color)
    draw = ImageDraw.Draw(output)

    # Calculate circle radius
    radius = (scale_factor * led_size_ratio) / 2

    # Draw each LED as a circle
    for y in range(height):
        for x in range(width):
            # Get pixel color
            color = tuple(pixels[y, x])

            # Calculate center of this LED cell
            center_x = x * scale_factor + scale_factor / 2
            center_y = y * scale_factor + scale_factor / 2

            # Draw circle (ellipse with equal width/height)
            bbox = [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ]
            draw.ellipse(bbox, fill=color)

    # Save as PNG
    output.save(output_path, "PNG")

    return output_path


def export_led_preview(
    input_path: str | Path,
    output_path: str | Path | None = None,
    mode: LedMode = LedMode.SQUARES,
    scale_factor: int = 10,
    background_color: tuple[int, int, int] = (0, 0, 0),
) -> Path:
    """Export snapshot with specified LED preview render mode.

    Renders the snapshot at the given scale using one of seven modes that
    match the interactive preview modes in the pro version of LED Portal.

    Each mode controls how individual LED pixels are visualised:

    | Mode                  | Description                                      |
    |-----------------------|--------------------------------------------------|
    | SQUARES               | Nearest-neighbour upscale (crisp square pixels)  |
    | CIRCLES_50            | 50% circles — wide gaps                          |
    | CIRCLES_75            | 75% circles — clear gaps                         |
    | CIRCLES_100           | 100% circles — edge-to-edge (tangent)            |
    | CIRCLES_125           | 125% circles — slight overlap between neighbours |
    | CIRCLES_CORNER        | ~141% circles — corner-touch, painter's algorithm|
    | CIRCLES_CORNER_BLEND  | ~141% circles — corner-touch, colour blending    |
    | GAUSSIAN              | Gaussian diffuser simulation (σ ≈ 27% of cell)  |

    Args:
        input_path: Path to input image file (BMP or PNG).
        output_path: Path to output PNG file. If None, appends '_{mode_name}' to stem.
        mode: Render mode. Default is SQUARES (same as export_blocks).
        scale_factor: Pixels per LED cell. Default is 10 (64×32 → 640×320).
        background_color: RGB background colour for non-circle areas. Default black.

    Returns:
        Path to the created PNG file.

    Example:
        >>> export_led_preview("snapshot.bmp", mode=LedMode.CIRCLES_100)
        PosixPath('snapshot_circles_100.png')
    """
    input_path = Path(input_path)
    if output_path is None:
        suffix = mode.name.lower()
        output_path = input_path.with_stem(f"{input_path.stem}_{suffix}").with_suffix(".png")
    else:
        output_path = Path(output_path)

    img = Image.open(input_path).convert("RGB")
    pixels = np.array(img)

    result = _render_led_array(pixels, mode, scale_factor, background_color)

    Image.fromarray(result, "RGB").save(output_path, "PNG")

    return output_path
