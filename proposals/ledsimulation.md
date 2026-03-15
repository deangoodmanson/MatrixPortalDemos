# LED Matrix Preview Simulation Modes

## Goal

Add an `o` key toggle to the live preview window that cycles through progressively more realistic visual simulations of what the 64×32 LED matrix actually looks like. Currently the preview uses a plain 10× nearest-neighbor scale (blocky squares). This proposal adds three circle-based render modes and the key-cycle mechanism to switch between them.

---

## Background and Context

### Current Preview Architecture

Both the `hs` and `pro` versions render the right-hand side of the preview window with identical logic:

```
enlarged = cv2.resize(small_frame, (64*10, 32*10), interpolation=cv2.INTER_NEAREST)
```

`small_frame` is the processed 64×32 BGR numpy array. The output is a 640×320 BGR image. In portrait mode this 640×320 image is then rotated 90° CCW before compositing with the camera view on the left.

**Pro**: enlargement logic lives in `pro/src/ledportal_pro/ui/overlay.py` → `show_preview()`.
**HS**: lives in `hs/src/camera_feed.py` → `show_preview()`.

### Reference Implementations

`utils/src/ledportal_utils/snapshot.py` contains two reference export functions:

- `export_blocks(path, scale_factor=10)` — PIL NEAREST resize, identical output to the current preview.
- `export_circles(path, scale_factor=10, led_size_ratio=0.9, background_color=(0,0,0))` — draws each LED as a circle using PIL `ImageDraw.ellipse`, on a black background. The `led_size_ratio` controls diameter as a fraction of cell size.

These are static file export utilities; they are not used at runtime. The new live preview renderer is independent of them but should produce visually equivalent output for the modes they cover.

---

## LED Simulation Modes

### Cell Geometry

The scale factor is `S = 10`. Each LED cell in the output image is an `S×S` pixel square. The center of cell `(col, row)` is at output coordinate:

```
cx = col * S + S/2    # = col*10 + 5
cy = row * S + S/2    # = row*10 + 5
```

Four modes are defined, differing only in the radius of the circle drawn for each LED:

---

### Mode 0: SQUARES (current behavior)

Each LED → filled `S×S` square, edge-to-edge, no gaps, no background visible.

**Render**: `cv2.resize(frame, (W*S, H*S), INTER_NEAREST)` — current code unchanged.
**Effective radius**: n/a (square geometry).
**Background visible**: no.

---

### Mode 1: CIRCLES_EDGE

Each LED → circle whose diameter equals the cell size. Circle touches all four edges of the cell but does not extend beyond. The four corners of the cell are exposed background.

**Radius**: `r = S / 2 = 5.0 px`
**Background visible**: yes — four small curved triangles at the corners of each cell.
**Adjacent circles**: do not touch or overlap. Gap between adjacent circle edges = 0 (they are tangent at the midpoint between cells).

*This is equivalent to `export_circles(scale_factor=10, led_size_ratio=1.0)`.*

---

### Mode 2: CIRCLES_CORNER

Each LED → circle whose edge passes through all four corners of the cell. The radius equals the distance from the cell center to a corner.

**Radius**: `r = (S / 2) × √2 = 5√2 ≈ 7.071 px`
**Background visible**: only at the exact single point where four cells meet (the four circles are tangent at that point — they meet but do not leave a gap). In practice on integer pixel grids this corner point becomes a tiny background pixel.
**Adjacent circles**: overlap. Two horizontally adjacent circles (centers 10 px apart, radius 7.071 each) overlap when `distance < 2r`, i.e., `10 < 14.14` — they do overlap. The overlap region is a lens shape centered on the shared cell edge, extending `r - S/2 = 2.071 px` on each side of the boundary.
**Rendering order**: painter's algorithm (draw all circles left-to-right, top-to-bottom); later circles overdraw earlier ones in the overlap region. This simulates the natural bleed of adjacent LEDs.

*This mode has no equivalent in the current utils library.*

---

### Mode 3: CIRCLES_75

Each LED → circle whose diameter is 75% of the cell size. Clear gaps between all circles. Background clearly visible.

**Radius**: `r = S × 0.375 = 3.75 px`
**Background visible**: yes — wide gaps between circles.
**Adjacent circles**: do not touch. Gap between circle edges = `S - 2r = 10 - 7.5 = 2.5 px`.

*This is equivalent to `export_circles(scale_factor=10, led_size_ratio=0.75)`.*

---

## Background Color

All circle modes render non-LED pixels with a configurable background color. The background is a constant RGB/BGR color for the whole canvas.

Two candidate defaults are documented for experimentation:

- **Black `(0, 0, 0)`** — matches the physical LED matrix bezel/gap color. Realistic for dark-room viewing.
- **White `(255, 255, 255)`** — makes gaps highly visible, useful for evaluating circle sizing at a desk.

The background color is a parameter to the render function, not a global or per-mode constant, so it can be changed independently of the mode cycle without re-adding another key binding. A separate key binding for background toggle (e.g., `O` / shift-O) is out of scope for this proposal but should be a natural follow-on.

**Recommended starting default**: black `(0, 0, 0)` to match physical hardware.

---

## Rendering Algorithm

### Non-overlapping modes (SQUARES, CIRCLES_EDGE, CIRCLES_75)

These modes can be rendered with a fully vectorized NumPy approach:

1. Upscale `small_frame` (64×32) to `enlarged` (640×320) using `cv2.INTER_NEAREST`. This assigns each output pixel the exact BGR color of its parent LED cell.
2. Compute a scalar distance array `dist[y, x]` = distance from each output pixel to the center of its cell. This is vectorizable because the distance only depends on the pixel's position **within** its cell, not on absolute coordinates:
   ```
   dx = (x_coordinate % S) - (S // 2)   # offset within cell, x axis
   dy = (y_coordinate % S) - (S // 2)   # offset within cell, y axis
   dist = sqrt(dx² + dy²)
   ```
   Both `dx` and `dy` arrays are `(320, 640)` and repeat with period `S`. They can be precomputed once and reused across frames.
3. Build boolean mask `inside_circle = dist <= r`.
4. Final output: pixels where `inside_circle` is True keep the upscaled LED color; pixels where it is False are set to `bg_color`.

For SQUARES mode, skip steps 2–4; the upscaled image is the output.

**NumPy implementation note**: `dx` and `dy` arrays can be created with `np.arange(out_W) % S - S//2` and `np.arange(out_H) % S - S//2` respectively, then broadcast via `np.meshgrid`. These are static for a given scale factor and should be pre-computed once (e.g., at initialization or on first call) and cached.

### Overlapping mode (CIRCLES_CORNER)

The modular distance trick does not correctly handle radii larger than `S/2` because each pixel is assigned to exactly one cell via integer division. For corner-touch circles, the radius (`5√2 ≈ 7.07`) exceeds `S/2 = 5`, meaning circles bleed into adjacent cells. The vectorized mask approach would not paint the bleed region since each pixel's `dist` is computed only against its own cell center.

**Use painter's algorithm**:

1. Create canvas: `output = np.full((H*S, W*S, 3), bg_color, dtype=uint8)`.
2. For each LED cell `(row, col)` in row-major order (top-to-bottom, left-to-right):
   - Compute center: `cx = col*S + S//2`, `cy = row*S + S//2`.
   - Get color: `color = small_frame[row, col]`.
   - Draw: `cv2.circle(output, (cx, cy), radius, color_tuple, thickness=-1)` (filled).
3. Later circles naturally overdraw earlier ones in overlap regions.

For 64×32 = 2048 LED cells, this inner loop runs 2048 `cv2.circle` calls per frame. OpenCV circle drawing is implemented in C; this is well within frame-rate budget for a 10–30 fps preview (empirically expect ~1–5 ms per frame on modern hardware).

**Rendering order note**: row-major (left-to-right, top-to-bottom) means the bottom-right LED of any overlap pair is the "winner." This is an arbitrary but consistent choice. Reverse order (right-to-left, bottom-to-top) is equally valid. The visual difference is only visible when adjacent LEDs differ in brightness.

---

## Portrait Mode Interaction

Portrait mode rotation is applied **after** the LED render, exactly as the current squares mode applies it:

```
if orientation == 'portrait':
    enlarged = cv2.rotate(enlarged, cv2.ROTATE_90_COUNTERCLOCKWISE)
```

No changes to portrait handling are required.

---

## Key Binding: `o` — Cycle Preview Render Mode

The `o` key cycles through the four modes in order, wrapping around:

```
SQUARES → CIRCLES_EDGE → CIRCLES_CORNER → CIRCLES_75 → SQUARES → ...
```

Pressing `o` when the preview window is disabled (preview toggled off via `w`) still advances the mode so that when preview is re-enabled it shows the newly selected mode.

The console should print a status line on each press, e.g.:
```
=== PREVIEW MODE: CIRCLES_CORNER (corner-touch, overlapping) ===
```

The mode name and a brief description should appear in `print_help` output.

---

## State and Data Flow

### New State Variable

Both versions require one new state variable in the main loop:

```
preview_render_mode  # cycles through the 4 modes
```

Default: `SQUARES` (index 0 / first mode).

### `render_led_preview` Function Signature (canonical)

```python
def render_led_preview(
    small_frame: np.ndarray,   # 64×32 BGR numpy array (the matrix frame)
    mode: PreviewMode,         # which render mode to use
    scale: int = 10,           # pixels per LED (output = frame * scale)
    bg_color: tuple = (0, 0, 0),  # BGR background color for non-LED pixels
) -> np.ndarray:               # output BGR image, shape (H*scale, W*scale, 3)
```

This function is the **only** change to `show_preview` internals — replace the `cv2.resize(INTER_NEAREST)` call with a call to `render_led_preview(small_frame, mode, scale, bg_color)`. All surrounding logic (camera-side scaling, blue capture-region rectangle, portrait rotation, `cv2.imshow`) is unchanged.

### `PreviewMode` Enum

```python
class PreviewMode(Enum):
    SQUARES = 0
    CIRCLES_EDGE = 1
    CIRCLES_CORNER = 2
    CIRCLES_75 = 3
```

Cycling: `PreviewMode((current.value + 1) % len(PreviewMode))`

---

## Changes Required Per File

### Pro Version

| File | Change |
|------|--------|
| `pro/src/ledportal_pro/ui/input.py` | Add `CYCLE_PREVIEW_MODE = auto()` to `InputCommand` enum; add `"o": InputCommand.CYCLE_PREVIEW_MODE` to `_parse_single_key` key map; add `"o"` branch to `_parse_line`; update `print_help` to show `o=cycle render mode` |
| `pro/src/ledportal_pro/ui/overlay.py` | Add `PreviewMode` enum; add `render_led_preview(small_frame, mode, scale, bg_color)` function; add pre-computed distance grid cache (module-level dict keyed by `(H, W, scale)`); modify `show_preview` to accept `render_mode: PreviewMode` parameter and call `render_led_preview` instead of direct `cv2.resize` |
| `pro/src/ledportal_pro/ui/__init__.py` | Export `PreviewMode` |
| `pro/src/ledportal_pro/main.py` | Import `PreviewMode`; add `preview_render_mode = PreviewMode.SQUARES` state variable; handle `InputCommand.CYCLE_PREVIEW_MODE`; pass `render_mode=preview_render_mode` to `show_preview`; add to reset handler (`preview_render_mode = PreviewMode.SQUARES`) |
| `pro/tests/test_input.py` | Add `"CYCLE_PREVIEW_MODE"` to `REQUIRED_COMMANDS` set |

### HS Version

| File | Change |
|------|--------|
| `hs/src/camera_feed.py` | Add `PreviewMode` enum (or simple string/int constant); add `render_led_preview(small_frame, mode, scale, bg_color)` function with educational comments; add `preview_render_mode` global; add `o` key handler in main loop; pass mode to `show_preview`; update `print_help`; add to reset handler |

---

## What Does NOT Change

- The saved snapshot `.bmp` file is always the raw 64×32 (or 32×64 portrait) matrix frame with no upscaling. The render mode is a preview-only concern.
- The `utils/` library functions (`export_blocks`, `export_circles`) are unchanged — they remain independent static export tools.
- The camera-side half of the preview window (with blue capture-region border) is unchanged.
- The `w` key (toggle preview on/off) is unchanged.
- The scale factor (10) is not exposed as a user-configurable value in this change.
- Mirror mode, B&W mode, zoom — all applied before the frame reaches `render_led_preview`.

---

## Open Questions for Iteration

1. **Background color default**: start with black; experiment with white. Consider a separate `O` (shift-O) key to toggle background between black and white.
2. **Circle antialiasing**: `cv2.circle` with `thickness=-1` does not antialias. PIL `ImageDraw.ellipse` also does not. For smoother circles, render at 2× scale then downscale (`INTER_AREA`), or use a floating-point distance mask with soft edge. Deferred to future iteration.
3. **Corner mode rendering order**: row-major (current proposal) vs. reverse order vs. Voronoi (nearest-center wins). Visually identical for most content; differs only on sharp LED color transitions.
4. **Naming**: `CIRCLES_CORNER` may be renamed `CIRCLES_OVERLAP` or `CIRCLES_BLEED` if that better communicates the intent after visual testing.
5. **Cached distance grid**: the pre-computed `dx/dy` arrays are constant for a given `(H, W, scale)`. They should be computed once and reused across frames for the non-overlapping modes. The painter's-algorithm loop for `CIRCLES_CORNER` does not benefit from this cache.
6. **Window title**: update `cv2.imshow` window title string to include current render mode, e.g., `"[ Camera ] | [ LED Matrix Preview ]    Note: The console must have window focus for keyboard commands. [circles-edge]"` so the mode is visible without checking the console.

---

## Mathematical Summary

| Mode | Radius (px, scale=10) | Circle fits in cell | Circles touch adjacent | Circles overlap | Background at corners |
|------|-----------------------|--------------------|-----------------------|-----------------|-----------------------|
| SQUARES | n/a | n/a | yes (edge) | no (filled square) | no |
| CIRCLES_EDGE | 5.0 | yes (tangent to all 4 edges) | tangent at midpoint | no | yes (4 small arcs) |
| CIRCLES_CORNER | ≈7.071 (5√2) | no (extends 2.07px beyond edge) | yes — overlap ~4.14px wide | yes | single point only |
| CIRCLES_75 | 3.75 | yes | no (2.5px gap) | no | yes (wide gaps) |
