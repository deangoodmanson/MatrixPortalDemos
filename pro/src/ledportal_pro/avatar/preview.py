"""On-screen avatar preview — no hardware required.

Run with:
    uv run ledportal-avatar preview <asset_dir> [--scale N]

Controls:
    1 / 2 / …  Cycle through the first / second / … feature's variants
    Q or Esc   Quit
"""

from __future__ import annotations

from pathlib import Path

import cv2

from .player import AvatarPlayer
from .schema import AvatarAsset


def run_preview(asset_dir: Path, scale: int = 8) -> None:
    """Open a scaled window showing the avatar with keyboard-driven expression cycling.

    Args:
        asset_dir: Directory containing avatar.yaml and PNG files.
        scale: Integer upscale factor for the 64×32 frame (default 8 → 512×256).
    """
    asset = AvatarAsset.load(asset_dir)
    player = AvatarPlayer(asset, asset_dir, transport=None)
    feature_list = list(asset.features.keys())

    _print_controls(asset)

    while True:
        frame_bytes = player.render_frame()
        bgr = _rgb565_to_bgr(frame_bytes, 64, 32)
        big = cv2.resize(bgr, (64 * scale, 32 * scale), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("Avatar Preview", big)

        key = cv2.waitKey(33) & 0xFF  # ~30 fps
        if key in (ord("q"), 27):  # Q or Esc
            break

        # Number keys 1-9 cycle through features in declaration order.
        for i, feature in enumerate(feature_list):
            if key == ord(str(i + 1)):
                spec = asset.features[feature]
                state = player.current_state()
                curr = state.get(feature, spec.variants[0])
                idx = spec.variants.index(curr)
                next_variant = spec.variants[(idx + 1) % len(spec.variants)]
                player.set_state(feature, next_variant)
                print(f"  {feature} → {next_variant}")
                break

    cv2.destroyAllWindows()


def _print_controls(asset: AvatarAsset) -> None:
    print(f"\nAvatar preview: {asset.source_session}")
    print(f"Palette: {len(asset.palette)} colours  |  Features: {list(asset.features)}")
    print("\nControls:")
    for i, (name, spec) in enumerate(asset.features.items()):
        print(f"  {i + 1} — cycle {name} ({len(spec.variants)} variants)")
    print("  Q / Esc — quit\n")


def _rgb565_to_bgr(data: bytes, width: int, height: int) -> cv2.typing.MatLike:  # type: ignore[name-defined]
    """Decode RGB565 bytes back to BGR for cv2.imshow."""
    import numpy as np

    raw = np.frombuffer(data, dtype="<u2").reshape((height, width))
    r = ((raw >> 11) & 0x1F) << 3
    g = ((raw >> 5) & 0x3F) << 2
    b = (raw & 0x1F) << 3
    rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
    import cv2 as _cv2

    return _cv2.cvtColor(rgb, _cv2.COLOR_RGB2BGR)
