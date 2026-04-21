"""Avatar player: composites an asset bundle and emits RGB565 frames.

The player loads all PNG layers once into memory (as numpy RGB arrays),
then renders on-demand by:
  1. Copying the base layer.
  2. Pasting each feature's current variant sprite at its anchor.
  3. Pasting any active overlays in declaration order.
  4. Converting RGB → BGR → RGB565 bytes via the existing pipeline.

State is set per-feature via `set_state(feature, variant)`. The player
is deliberately stateless about timing — callers control when to call
`render_frame()` and whether to push to transport.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image

from ..processing.color import convert_to_rgb565
from .schema import AvatarAsset, OverlaySpec

if TYPE_CHECKING:
    from ..transport.base import TransportBase


class AvatarPlayer:
    """Composites an avatar asset for display on the LED matrix.

    Args:
        asset: Loaded AvatarAsset (schema metadata).
        asset_dir: Directory containing the PNG files referenced by the asset.
        transport: Optional transport for sending frames to the matrix.
        preview_scale: If > 0, show a scaled preview window on every render.
            Uses INTER_NEAREST upscaling (default 0 = no window).
    """

    def __init__(
        self,
        asset: AvatarAsset,
        asset_dir: Path,
        transport: TransportBase | None = None,
        preview_scale: int = 0,
    ) -> None:
        self._asset = asset
        self._transport = transport
        self._preview_scale = preview_scale

        # Palette as (N, 3) uint8 RGB lookup table.
        self._palette_rgb: NDArray[np.uint8] = np.array(
            [[c.r, c.g, c.b] for c in asset.palette], dtype=np.uint8
        )

        # Base layer as (32, 64, 3) uint8 RGB.
        self._base_rgb = self._load_indexed_as_rgb(asset_dir / asset.base.file)

        # Feature sheets as {name: (sh, sheet_w) uint8 index arrays}.
        self._sheets: dict[str, NDArray[np.uint8]] = {
            name: np.array(Image.open(str(asset_dir / spec.sheet)), dtype=np.uint8)
            for name, spec in asset.features.items()
        }

        # Overlays as list of (spec, (oh, ow) uint8 index arrays).
        self._overlays: list[tuple[OverlaySpec, NDArray[np.uint8]]] = [
            (ovl, np.array(Image.open(str(asset_dir / ovl.file)), dtype=np.uint8))
            for ovl in asset.overlays
        ]

        # Current state: feature → variant name. Default to first variant.
        self._state: dict[str, str] = {
            name: spec.variants[0] for name, spec in asset.features.items() if spec.variants
        }

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def set_state(self, feature: str, variant: str) -> None:
        """Set the active variant for a feature.

        Args:
            feature: Feature name (e.g. "eyes", "mouth").
            variant: Variant name from the feature's variants list.

        Raises:
            KeyError: If feature or variant is unknown.
        """
        if feature not in self._asset.features:
            raise KeyError(f"Unknown feature {feature!r}")
        spec = self._asset.features[feature]
        if variant not in spec.variants:
            raise KeyError(f"Unknown variant {variant!r} for {feature!r}")
        self._state[feature] = variant

    def current_state(self) -> dict[str, str]:
        """Return a copy of the current feature → variant state."""
        return dict(self._state)

    def render_frame(self) -> bytes:
        """Composite all layers and return an RGB565 byte string (4096 bytes)."""
        frame = self._base_rgb.copy()

        for name, spec in self._asset.features.items():
            variant = self._state.get(name)
            if variant is None:
                continue
            vi = spec.variant_index(variant)
            sw, sh = spec.sprite_size
            ax, ay = spec.anchor
            sprite_indices = self._sheets[name][:sh, vi * sw : (vi + 1) * sw]
            self._paste_indexed(frame, sprite_indices, ax, ay)

        for ovl_spec, ovl_indices in self._overlays:
            ax, ay = ovl_spec.anchor
            self._paste_indexed(frame, ovl_indices, ax, ay)

        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        if self._preview_scale > 0:
            big = cv2.resize(
                frame_bgr,
                (64 * self._preview_scale, 32 * self._preview_scale),
                interpolation=cv2.INTER_NEAREST,
            )
            cv2.imshow("Avatar", big)
            cv2.waitKey(1)
        return convert_to_rgb565(frame_bgr)

    def send_frame(self) -> None:
        """Render and push current frame to the transport (if connected)."""
        if self._transport is not None:
            self._transport.send_frame(self.render_frame())

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _load_indexed_as_rgb(self, path: Path) -> NDArray[np.uint8]:
        """Load a palette-mode PNG and expand to (H, W, 3) RGB."""
        img = Image.open(str(path))
        indices = np.array(img, dtype=np.uint8)
        return self._palette_rgb[indices]

    def _paste_indexed(
        self,
        frame: NDArray[np.uint8],
        indices: NDArray[np.uint8],
        ax: int,
        ay: int,
    ) -> None:
        """Paint an indexed sprite onto frame at anchor (ax, ay).

        Clips silently to frame bounds. MVP: all sprite pixels overwrite
        (no per-pixel transparency — sprites are tight face crops).
        """
        fh, fw = frame.shape[:2]
        sh, sw = indices.shape[:2]

        y1 = max(0, ay)
        y2 = min(fh, ay + sh)
        x1 = max(0, ax)
        x2 = min(fw, ax + sw)
        if y2 <= y1 or x2 <= x1:
            return

        sy1, sx1 = y1 - ay, x1 - ax
        sprite_rgb = self._palette_rgb[indices[sy1 : sy1 + (y2 - y1), sx1 : sx1 + (x2 - x1)]]
        frame[y1:y2, x1:x2] = sprite_rgb
