"""Build an avatar asset bundle from a capture session directory.

Pipeline:
  1. Load session manifest; locate the front-neutral base pose.
  2. Extract a shared colour palette from the base image (PIL median-cut).
  3. Detect face feature regions (eyes, mouth) via MediaPipe Face Landmarker
     if the model is present, otherwise fall back to proportion heuristics.
  4. For each captured pose, crop and palette-quantize an eye sprite and a
     mouth sprite.
  5. Assemble sprites into horizontal PNG sprite sheets (one per feature).
  6. Write base.png (palette-quantized 64×32) and avatar.yaml to output_dir.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from .schema import (
    SCHEMA_VERSION,
    AvatarAsset,
    BaseLayerSpec,
    PaletteColor,
    SpriteSheetSpec,
)

# MediaPipe Face Landmarker model — downloaded on demand via --download-model.
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

# Landmark indices used for bounding-box extraction (MediaPipe 478-point model).
_EYE_LANDMARKS = [33, 159, 133, 145, 362, 386, 263, 374, 173, 398]
_MOUTH_LANDMARKS = [61, 291, 0, 17, 185, 409, 375, 321]

# Padding added around detected bounding boxes (fraction of image dimensions).
_REGION_PAD_X = 0.05
_REGION_PAD_Y = 0.04


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #


def build_avatar(
    session_dir: Path,
    output_dir: Path,
    palette_size: int = 8,
    model_path: Path | None = None,
) -> AvatarAsset:
    """Build a complete avatar asset bundle from a capture session.

    Args:
        session_dir: Directory containing manifest.json and captured BMP/PNG files.
        output_dir: Destination for the generated asset bundle.
        palette_size: Number of palette colours (4-16).
        model_path: Path to face_landmarker.task model. Heuristic fallback used
            if None or path does not exist, or if mediapipe is not installed.

    Returns:
        The constructed AvatarAsset (also saved as avatar.yaml in output_dir).
    """
    if not 4 <= palette_size <= 16:
        raise ValueError(f"palette_size must be 4-16, got {palette_size}")

    manifest = _load_manifest(session_dir)
    captured: list[dict[str, Any]] = manifest.get("captured", [])
    session_time: str = manifest.get("session", "unknown")

    if not captured:
        raise ValueError(f"No captured poses in {session_dir}")

    print(f"Building avatar from {session_dir.name} ({len(captured)} poses)…")

    # Step 1 — palette from base (full-res raw preferred, BMP fallback).
    base_full_bgr = _load_pose_image(session_dir, _find_pose(captured, "front", "neutral"))
    palette = _extract_palette(base_full_bgr, palette_size)
    print(f"  Palette: {palette_size} colours extracted")

    # Step 2 — feature regions (normalised 0-1).
    regions = _detect_feature_regions(base_full_bgr, model_path)
    print(f"  Regions: {', '.join(regions)}")

    # Step 3 — determine sprite sizes + anchors in 64×32 coordinates.
    base_w, base_h = 64, 32
    sprite_sizes: dict[str, tuple[int, int]] = {}
    anchors: dict[str, tuple[int, int]] = {}
    for feature, (nx1, ny1, nx2, ny2) in regions.items():
        ax, ay = int(nx1 * base_w), int(ny1 * base_h)
        sw = max(2, int((nx2 - nx1) * base_w))
        sh = max(1, int((ny2 - ny1) * base_h))
        sprite_sizes[feature] = (sw, sh)
        anchors[feature] = (ax, ay)

    # Step 4 — extract sprites for every captured pose.
    sprites: dict[str, list[Image.Image]] = {f: [] for f in regions}
    variants: dict[str, list[str]] = {f: [] for f in regions}

    for pose in captured:
        variant = f"{pose['angle']}_{pose['expression']}"
        pose_bgr = _load_pose_image(session_dir, pose)
        if pose_bgr is None:
            print(f"    Warning: {variant} — image not found, skipping")
            continue

        ph, pw = pose_bgr.shape[:2]
        for feature, (nx1, ny1, nx2, ny2) in regions.items():
            bbox = (int(nx1 * pw), int(ny1 * ph), int(nx2 * pw), int(ny2 * ph))
            sprite = _extract_sprite(pose_bgr, bbox, sprite_sizes[feature], palette)
            sprites[feature].append(sprite)
            variants[feature].append(variant)

    print(f"  Sprites: {[f'{f}×{len(sprites[f])}' for f in sprites]}")

    # Step 5 — build sheets + save.
    output_dir.mkdir(parents=True, exist_ok=True)
    feature_specs: dict[str, SpriteSheetSpec] = {}

    for feature in regions:
        if not sprites[feature]:
            continue
        sheet = _build_sheet(sprites[feature], sprite_sizes[feature], palette)
        sheet_file = f"{feature}_sheet.png"
        sheet.save(str(output_dir / sheet_file))
        feature_specs[feature] = SpriteSheetSpec(
            sheet=sheet_file,
            sprite_size=sprite_sizes[feature],
            anchor=anchors[feature],
            variants=variants[feature],
        )

    # Step 6 — base.png (always from the 64×32 BMP).
    base_bmp_bgr = _load_base_bmp(session_dir, manifest)
    base_indexed = _map_to_palette(base_bmp_bgr, palette)
    base_indexed.save(str(output_dir / "base.png"))

    # Step 7 — asset manifest.
    asset = AvatarAsset(
        version=SCHEMA_VERSION,
        source_session=session_time,
        palette=palette,
        base=BaseLayerSpec(file="base.png"),
        features=feature_specs,
        metadata={
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "palette_size": str(palette_size),
            "pose_count": str(len(captured)),
        },
    )
    asset.save(output_dir)
    print(f"  Done → {output_dir}/")
    return asset


def default_model_path() -> Path:
    """Return the default location for the Face Landmarker model file."""
    return Path.home() / ".cache" / "ledportal" / "face_landmarker.task"


def download_model(path: Path | None = None) -> Path:
    """Download the MediaPipe Face Landmarker model if not already present.

    Args:
        path: Where to save the model. Defaults to `default_model_path()`.

    Returns:
        Path to the (now-present) model file.
    """
    dest = path or default_model_path()
    if dest.exists():
        print(f"Model already present: {dest}")
        return dest
    print(f"Downloading Face Landmarker model → {dest} …")
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(_MODEL_URL, dest)
    print("  Download complete.")
    return dest


# --------------------------------------------------------------------------- #
# Palette                                                                     #
# --------------------------------------------------------------------------- #


def _extract_palette(image_bgr: np.ndarray, n_colors: int) -> list[PaletteColor]:
    """Extract N dominant colours from a BGR image using PIL median-cut.

    Uses the quantised image itself (via convert("RGB")) to read palette
    entries rather than `getpalette()`, which changed behaviour in
    Pillow 10/11 and may return fewer bytes than expected.  Palette slots
    with no pixels in the quantised image are padded with black.
    """
    rgb_pil = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    quantized = rgb_pil.quantize(
        colors=n_colors,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    rgb_back = quantized.convert("RGB")
    idx_arr = np.array(quantized, dtype=np.uint8)
    rgb_arr = np.array(rgb_back, dtype=np.uint8)

    palette: list[PaletteColor] = []
    for i in range(n_colors):
        ys, xs = np.where(idx_arr == i)
        if len(ys) > 0:
            c = rgb_arr[ys[0], xs[0]]
            palette.append(PaletteColor(int(c[0]), int(c[1]), int(c[2])))
        else:
            palette.append(PaletteColor(0, 0, 0))
    return palette


def _map_to_palette(image_bgr: np.ndarray, palette: list[PaletteColor]) -> Image.Image:
    """Return a palette-mode (P) PIL image with pixels snapped to nearest palette entry.

    Uses vectorised L2 distance — correct regardless of PIL's internal
    quantise ordering.
    """
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
    pal = np.array([[c.r, c.g, c.b] for c in palette], dtype=np.float32)
    diff = rgb[:, :, np.newaxis, :] - pal[np.newaxis, np.newaxis, :, :]
    indices = np.argmin(np.sum(diff * diff, axis=-1), axis=-1).astype(np.uint8)
    h, w = indices.shape
    img = Image.frombytes("P", (w, h), indices.tobytes())
    img.putpalette(_flat_palette(palette))
    return img


# --------------------------------------------------------------------------- #
# Landmark detection                                                          #
# --------------------------------------------------------------------------- #


def _detect_feature_regions(
    image_bgr: np.ndarray,
    model_path: Path | None,
) -> dict[str, tuple[float, float, float, float]]:
    """Return normalised (x1, y1, x2, y2) bounding boxes for 'eyes' and 'mouth'.

    Tries MediaPipe Face Landmarker first; falls back to heuristics if the
    model is absent or mediapipe is not installed.
    """
    if model_path is not None and model_path.exists():
        result = _try_mediapipe_regions(image_bgr, model_path)
        if result is not None:
            return result
    return _heuristic_regions()


def _heuristic_regions() -> dict[str, tuple[float, float, float, float]]:
    """Proportion-based bounding boxes for a face filling the frame."""
    return {
        "eyes": (0.08, 0.28, 0.92, 0.50),
        "mouth": (0.18, 0.62, 0.82, 0.82),
    }


def _try_mediapipe_regions(
    image_bgr: np.ndarray,
    model_path: Path,
) -> dict[str, tuple[float, float, float, float]] | None:
    """Detect feature regions with MediaPipe Face Landmarker.

    Returns normalised regions, or None if detection fails or mediapipe
    is not installed.
    """
    try:
        import mediapipe as mp  # type: ignore[import-untyped]
        from mediapipe.tasks import python as mp_python  # type: ignore[import-untyped]
        from mediapipe.tasks.python import vision as mp_vision  # type: ignore[import-untyped]
    except ImportError:
        return None

    base_opts = mp_python.BaseOptions(model_asset_path=str(model_path))
    opts = mp_vision.FaceLandmarkerOptions(base_options=base_opts, num_faces=1)

    try:
        with mp_vision.FaceLandmarker.create_from_options(opts) as detector:
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_img)
    except Exception:
        return None

    if not result.face_landmarks:
        return None

    lm = result.face_landmarks[0]

    def bbox(indices: list[int], pad_x: float, pad_y: float) -> tuple[float, float, float, float]:
        xs = [lm[i].x for i in indices]
        ys = [lm[i].y for i in indices]
        return (
            max(0.0, min(xs) - pad_x),
            max(0.0, min(ys) - pad_y),
            min(1.0, max(xs) + pad_x),
            min(1.0, max(ys) + pad_y),
        )

    return {
        "eyes": bbox(_EYE_LANDMARKS, _REGION_PAD_X, _REGION_PAD_Y),
        "mouth": bbox(_MOUTH_LANDMARKS, _REGION_PAD_X, _REGION_PAD_Y),
    }


# --------------------------------------------------------------------------- #
# Sprite extraction and sheet assembly                                        #
# --------------------------------------------------------------------------- #


def _extract_sprite(
    image_bgr: np.ndarray,
    bbox: tuple[int, int, int, int],
    sprite_size: tuple[int, int],
    palette: list[PaletteColor],
) -> Image.Image:
    """Crop bbox from image, resize to sprite_size, apply palette.

    Returns a palette-mode PIL Image.
    """
    x1, y1, x2, y2 = bbox
    h, w = image_bgr.shape[:2]
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    crop = image_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        crop = np.zeros((sprite_size[1], sprite_size[0], 3), dtype=np.uint8)
    resized = cv2.resize(crop, sprite_size, interpolation=cv2.INTER_NEAREST)
    return _map_to_palette(resized, palette)


def _build_sheet(
    sprites: list[Image.Image],
    sprite_size: tuple[int, int],
    palette: list[PaletteColor],
) -> Image.Image:
    """Assemble a horizontal strip of palette-mode sprites."""
    sw, sh = sprite_size
    n = len(sprites)
    sheet_arr = np.zeros((sh, sw * n), dtype=np.uint8)
    for i, sprite in enumerate(sprites):
        arr = np.array(sprite, dtype=np.uint8)
        sheet_arr[:sh, i * sw : (i + 1) * sw] = arr[:sh, :sw]
    img = Image.frombytes("P", (sw * n, sh), sheet_arr.tobytes())
    img.putpalette(_flat_palette(palette))
    return img


# --------------------------------------------------------------------------- #
# Image loading helpers                                                       #
# --------------------------------------------------------------------------- #


def _load_manifest(session_dir: Path) -> dict[str, Any]:
    path = session_dir / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"No manifest.json in {session_dir}")
    with open(path) as f:
        return json.load(f)  # type: ignore[no-any-return]


def _find_pose(
    captured: list[dict[str, Any]],
    angle: str,
    expression: str,
) -> dict[str, Any]:
    for pose in captured:
        if pose["angle"] == angle and pose["expression"] == expression:
            return pose
    return captured[0]  # fallback to first pose


def _load_pose_image(
    session_dir: Path,
    pose: dict[str, Any],
) -> np.ndarray:
    """Load a pose image: full-res raw PNG preferred, 64×32 BMP fallback."""
    raw_name = pose.get("raw_file")
    if raw_name:
        raw_path = session_dir / raw_name
        if raw_path.exists():
            img = cv2.imread(str(raw_path))
            if img is not None:
                return img
    bmp_path = session_dir / pose["file"]
    img = cv2.imread(str(bmp_path))
    if img is not None:
        return img
    raise FileNotFoundError(f"Image not found for pose {pose}")


def _load_base_bmp(session_dir: Path, manifest: dict[str, Any]) -> np.ndarray:
    """Load the front_neutral BMP (always 64×32) to use as the base layer."""
    captured: list[dict[str, Any]] = manifest.get("captured", [])
    pose = _find_pose(captured, "front", "neutral")
    bmp_path = session_dir / pose["file"]
    img = cv2.imread(str(bmp_path))
    if img is None:
        raise FileNotFoundError(f"Base BMP not found: {bmp_path}")
    return img


# --------------------------------------------------------------------------- #
# Utilities                                                                   #
# --------------------------------------------------------------------------- #


def _flat_palette(palette: list[PaletteColor]) -> list[int]:
    """Return a 768-byte flat palette list for PIL (padded to 256 entries)."""
    flat: list[int] = []
    for c in palette:
        flat.extend([c.r, c.g, c.b])
    flat.extend([0] * (768 - len(flat)))
    return flat
