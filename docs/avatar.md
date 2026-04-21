# Avatar Feature

Builds a pixel-art face avatar from a capture session and plays it on the 64x32 LED matrix (or previews it on-screen). Expressions are controlled in real time by a keyboard or live webcam face tracking.

The intentionally low resolution produces a pixel-art aesthetic that sidesteps the uncanny valley: our brains don't expect photorealism from 2,048 pixels.

---

## How it Works

The avatar pipeline has three layers:

**1. Capture and asset build**
You photograph yourself in 25 poses using the built-in capture session. The builder palette-quantizes all frames to a shared 4–16 color indexed palette, then slices out eye and mouth regions as independent sprite sheets. The result is an `avatar.yaml` asset bundle — a set of tiny indexed PNGs, one strip per facial feature.

**2. Compositing**
At runtime, `AvatarPlayer` holds the base face layer and one sprite sheet per feature (eyes, mouth). Each frame, it pastes the active variant sprite at its anchor point on the base, then converts the result to RGB565 for the LED matrix. Swapping an expression is just changing which sprite column is pasted — no re-rendering.

**3. Expression control (webcam driver)**
The webcam driver uses **MediaPipe Face Landmarker**, a pre-trained MobileNet-based neural network that runs locally on every camera frame. It outputs 478 face landmarks and 52 ARKit blendshape coefficients — per-feature scores like `eyeBlinkLeft` (0.0–1.0), `jawOpen`, `mouthSmileLeft`, etc. These coefficients are threshold-mapped to semantic states (`eyes="closed"`, `mouth="smile"`) which the `VariantResolver` then looks up in the asset to find the best matching sprite.

Because inference runs on-device, the webcam driver requires no internet connection and has no usage cost after the one-time model download (~2 MB).

---

## Quick Start

```bash
# 1. During a live ledportal session, press v to start a capture session.
#    Follow the voice prompts. The session directory is written to pro/.

# 2. Build an avatar asset bundle from the session.
uv run ledportal-avatar build avatar_20260420_123456/

# 3. Preview on-screen (no hardware needed).
uv run ledportal-avatar preview avatar_asset_avatar_20260420_123456/

# 4. Play on the LED matrix with a live preview window.
uv run ledportal-avatar play avatar_asset_avatar_20260420_123456/ --port /dev/ttyACM0 --preview
```

---

## Step 1: Capture a Session

Press `v` during a running `ledportal` session to start an avatar capture. The system guides you through **25 poses** across five head angles (front, left, right, up, down) with voice prompts so you can keep your eyes on the camera.

For each pose:
- Press `Space` to capture the pose (a burst of 5 frames is taken; the sharpest one is kept).
- Press `S` to skip the current pose.
- Press `R` to repeat the voice prompt.
- Press `Q` to quit the session early.

### Output layout

```
avatar_YYYYMMDD_HHMMSS/
├── manifest.json                          # structured metadata for every captured pose
├── avatar_<angle>_<expression>.bmp        # 64x32 downsample of the pose
├── avatar_<angle>_<expression>.bin        # RGB565 binary (4096 bytes)
└── avatar_<angle>_<expression>_raw.png    # full-resolution camera frame (for landmark detection)
```

`manifest.json` records the angle, expression, filename, raw filename, sharpness score (Laplacian variance of the winning burst frame), and burst size for every captured pose.

---

## Step 2: Build the Asset

```bash
uv run ledportal-avatar build SESSION_DIR [options]
```

| Argument / Flag | Default | Description |
|---|---|---|
| `SESSION_DIR` | (required) | Path to the capture session directory containing `manifest.json`. |
| `--output DIR`, `-o DIR` | `../avatar_asset_<name>` | Where to write the asset bundle. |
| `--palette-size N`, `-n N` | `8` | Number of palette colors (4-16). Fewer = more stylized. |
| `--model PATH` | `~/.cache/ledportal/face_landmarker.task` | Path to the MediaPipe `face_landmarker.task` model. Falls back to proportion heuristics if absent. |
| `--download-model` | off | Download the Face Landmarker model before building (requires internet access). |

### Build pipeline

1. Loads `manifest.json` and locates the `front_neutral` base pose.
2. Extracts a shared color palette (PIL median-cut) from the base pose's full-resolution raw frame.
3. Detects eye and mouth feature regions via MediaPipe Face Landmarker (478-point model). Falls back to fixed proportions if the model is absent or mediapipe is not installed.
4. For each captured pose, crops the eye and mouth regions, resizes to sprite dimensions, and palette-quantizes them.
5. Assembles sprites into horizontal PNG sprite sheets (one per feature).
6. Writes `base.png` (palette-quantized 64x32) and `avatar.yaml` to the output directory.

### Output layout

```
avatar_asset_<name>/
├── avatar.yaml        # metadata: palette, anchors, variant list, schema version
├── base.png           # 64x32 indexed-color PNG (no transparency)
├── eyes_sheet.png     # horizontal strip of eye variants
└── mouth_sheet.png    # horizontal strip of mouth variants
```

---

## Step 3: Preview

```bash
uv run ledportal-avatar preview ASSET_DIR [--scale N]
```

| Flag | Default | Description |
|---|---|---|
| `--scale N` | `8` | Upscale factor applied to the 64x32 frame for on-screen display. |

Preview uses the keyboard driver (same key map as `play`). Press `Q` or `Esc` to exit.

---

## Step 4: Play

```bash
uv run ledportal-avatar play ASSET_DIR [options]
```

| Flag | Default | Description |
|---|---|---|
| `--driver DRIVER` | `keyboard` | Input driver: `keyboard` or `webcam`. (`audio` is not yet implemented.) |
| `--no-blink` | off | Disable automatic blink injection. |
| `--port PORT` | (none) | Serial port for the LED matrix (e.g. `/dev/ttyACM0`). Omit to run without hardware. |
| `--fps FPS` | `15` | Target frame rate. |
| `--preview` | off | Show a live on-screen window displaying exactly what is sent to the matrix. |
| `--preview-scale N` | `8` | Upscale factor for the preview window (default 8 → 512×256). |
| `--webcam-index N` | `0` | Camera device index for `--driver webcam`. |
| `--webcam-model PATH` | `~/.cache/ledportal/face_landmarker.task` | Path to `face_landmarker.task` for the webcam driver. |

`--preview` works with or without `--port` — useful for testing expressions without hardware, or for monitoring what is being sent to the matrix while it plays.

---

## Drivers

### Keyboard Driver

The default driver. Uses non-blocking terminal input; each poll drains all pending keypresses and applies the last relevant key per category.

| Key(s) | Category | Semantic |
|---|---|---|
| `1` | Eyes | `open` |
| `2` | Eyes | `closed` |
| `3` | Eyes | `raised` |
| `4` | Eyes | `furrowed` |
| `5` | Mouth | `neutral` |
| `6` | Mouth | `smile` |
| `7` | Mouth | `smile_open` |
| `8` | Mouth | `o` |
| `9` | Mouth | `ee` |
| `W` | Angle | `up` |
| `S` | Angle | `down` |
| `A` | Angle | `left` |
| `D` | Angle | `right` |
| `E` | Angle | `front` |
| `Q` or `Esc` | — | Stop |

Keys are case-insensitive. Unrecognized keys are ignored.

### Webcam Driver

Runs MediaPipe Face Landmarker on a live OpenCV camera stream. Blendshape coefficients map to eye and mouth semantics; the facial transformation matrix provides yaw and pitch for the angle.

**Requirements:**

```bash
uv pip install 'ledportal-pro[avatar]'
```

A `face_landmarker.task` model file must be present:

```bash
uv run ledportal-avatar build --download-model SESSION_DIR
```

The model is downloaded to `~/.cache/ledportal/face_landmarker.task` by default and reused by both `build` and `play`.

#### Blendshape thresholds

| Blendshape(s) | Condition | Semantic |
|---|---|---|
| `eyeBlinkLeft` / `eyeBlinkRight` avg | > 0.55 | `eyes="closed"` |
| `browInnerUp` + `browOuterUpLeft` + `browOuterUpRight` avg | > 0.30 | `eyes="raised"` |
| `browDownLeft` / `browDownRight` avg | > 0.30 | `eyes="furrowed"` |
| (none of the above) | — | `eyes="open"` |
| `jawOpen` | > 0.40 | `mouth="o"` |
| `mouthSmileLeft` / `mouthSmileRight` avg > 0.35 AND `jawOpen` > 0.25 | — | `mouth="smile_open"` |
| `mouthSmileLeft` / `mouthSmileRight` avg | > 0.35 | `mouth="smile"` |
| `mouthFunnel` | > 0.30 | `mouth="ee"` |
| (none of the above) | — | `mouth="neutral"` |

#### Angle from head orientation

Yaw and pitch are extracted from the 4x4 facial transformation matrix using ZYX Euler decomposition.

| Range | Angle |
|---|---|
| yaw > +20 degrees | `"right"` |
| yaw < -20 degrees | `"left"` |
| pitch < -15 degrees | `"up"` |
| pitch > +15 degrees | `"down"` |
| (else) | `"front"` |

When no face is detected in a frame, the driver returns the last known state.

### BlinkFilter

`BlinkFilter` is driver middleware that wraps any driver and injects brief `eyes="closed"` overrides at randomized intervals (3-7 seconds by default, lasting 0.12 seconds), simulating natural blinking. It is active by default.

To disable:

```bash
uv run ledportal-avatar play ASSET_DIR --no-blink
```

Blink injection is suppressed when the inner driver already reports `eyes="closed"` (e.g. during an expression that closes the eyes), so blinking does not fight deliberate closed-eye states.

---

## Asset Format

`avatar.yaml` is the single source of truth for an asset bundle. Schema version 1.

```yaml
version: 1
source_session: "2026-04-20T12:34:56"
metadata:
  built_at: "2026-04-20T12:35:10"
  palette_size: "8"
  pose_count: "25"
palette:
  - "#1a1a2e"
  - "#f5c5a3"
  # ... (4-16 entries total, RGB888 hex)
base:
  file: base.png
  size: [64, 32]
features:
  eyes:
    sheet: eyes_sheet.png
    sprite_size: [32, 6]       # [width, height] in pixels
    anchor: [16, 10]           # top-left position on the 64x32 canvas
    variants:
      - front_neutral
      - front_smile
      # ... one entry per sprite column in the sheet
    transparent_index: 0       # palette index treated as alpha
  mouth:
    sheet: mouth_sheet.png
    sprite_size: [26, 5]
    anchor: [19, 20]
    variants:
      - front_neutral
      - front_smile
      # ...
    transparent_index: 0
overlays: []                   # optional list of named overlay layers
```

**Key rules:**
- Palette entries are 4-16 `#RRGGBB` hex strings. RGB565 conversion happens at render time.
- Sprite sheets are horizontal strips of equal-width variants. Variant `name` starts at pixel column `variants.index(name) * sprite_size[0]`.
- Anchors are `[x, y]` top-left coordinates in PIL convention (origin top-left, y grows down).
- `transparent_index` references a palette index; that color is treated as transparent when compositing.
- Overlays are drawn last, in declaration order, over all features.
- State machine and driver logic live in code, not in this file.

### Variant naming convention

Variants follow the pattern `{angle}_{expression}`:

```
front_neutral
front_smile
front_eyes_closed
left_neutral
right_mouth_o
up_eyebrows_up
```

Valid angles: `front`, `left`, `right`, `up`, `down`.

---

## Expression Semantics

The `VariantResolver` maps semantic `DriverState` fields (`eyes`, `mouth`) to concrete variant names using this fixed table:

| Expression name (in variant) | Eye semantic | Mouth semantic |
|---|---|---|
| `neutral` | `open` | `neutral` |
| `smile` | `open` | `smile` |
| `smile_open` | `open` | `smile_open` |
| `eyebrows_up` | `raised` | `neutral` |
| `eyes_closed` | `closed` | `neutral` |
| `mouth_o` | `open` | `o` |
| `mouth_ee` | `open` | `ee` |
| `mouth_closed` | `open` | `closed` |
| `furrowed` | `furrowed` | `neutral` |

The resolver indexes eye and mouth variants independently, so a driver can set `mouth="smile"` while leaving eyes unchanged. This enables combinatorial expressions (e.g. raised brows + smile open mouth) from a captured set that never explicitly combined them.

### Fallback chain

When an exact `(angle, semantic)` match is not found, the resolver falls back in order:

1. Exact `(angle, semantic)` match.
2. `("front", semantic)` — front-facing fallback.
3. Any variant with that semantic, regardless of angle.
4. First variant in the asset (last resort).

---

## Installing the Mediapipe Extra

The webcam driver and the MediaPipe-assisted build path require the `avatar` optional dependency group:

```bash
uv pip install 'ledportal-pro[avatar]'
```

This installs `mediapipe` alongside the base package. The base `ledportal-pro` install does not require mediapipe; the build pipeline falls back to proportion heuristics when it is absent.

---

## Troubleshooting

**Camera not found (`--driver webcam`)**

```
RuntimeError: Cannot open camera 0
```

Try a different device index:

```bash
uv run ledportal-avatar play ASSET_DIR --driver webcam --webcam-index 1
```

**Model not found**

```
Error: face_landmarker.task not found at ~/.cache/ledportal/face_landmarker.task
```

Download it:

```bash
uv run ledportal-avatar build --download-model SESSION_DIR
```

Or specify a custom path:

```bash
uv run ledportal-avatar play ASSET_DIR --driver webcam --webcam-model /path/to/face_landmarker.task
```

**No face detected**

The webcam driver returns the last known `DriverState` when MediaPipe finds no face in a frame. The avatar holds its previous expression until a face is detected again. This is intentional — it avoids flickering during brief occlusions.

**Build falls back to heuristics**

If `--model` is omitted and `~/.cache/ledportal/face_landmarker.task` does not exist (or mediapipe is not installed), the builder uses fixed proportions for eye and mouth regions:

- Eyes: normalized region `(0.08, 0.28, 0.92, 0.50)`
- Mouth: normalized region `(0.18, 0.62, 0.82, 0.82)`

This works for faces that fill most of the frame but will be less precise than landmark-guided detection. Run `--download-model` and install the `avatar` extra for best results.
