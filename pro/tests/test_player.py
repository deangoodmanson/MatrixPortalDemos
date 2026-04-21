"""Tests for AvatarPlayer compositing.

All tests use synthetic in-memory assets — no real session directories or
capture runs needed. The player is constructed directly from schema objects
and temporary PNG files.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ledportal_pro.avatar.builder import _flat_palette
from ledportal_pro.avatar.player import AvatarPlayer
from ledportal_pro.avatar.schema import (
    SCHEMA_VERSION,
    AvatarAsset,
    BaseLayerSpec,
    PaletteColor,
    SpriteSheetSpec,
)

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

_RED = PaletteColor(255, 0, 0)
_GREEN = PaletteColor(0, 255, 0)
_BLUE = PaletteColor(0, 0, 255)
_BLACK = PaletteColor(0, 0, 0)

_PALETTE_4 = [_RED, _GREEN, _BLUE, _BLACK]


def _indexed_png(path: Path, arr: np.ndarray, palette: list[PaletteColor]) -> None:
    """Write a palette-mode PNG with the given index array."""
    h, w = arr.shape
    img = Image.frombytes("P", (w, h), arr.astype(np.uint8).tobytes())
    img.putpalette(_flat_palette(palette))
    img.save(str(path))


def _make_asset_dir(
    tmp_path: Path,
    base_indices: np.ndarray,
    eyes_variants: list[np.ndarray],
    mouth_variants: list[np.ndarray],
    palette: list[PaletteColor] = _PALETTE_4,
) -> tuple[Path, AvatarAsset]:
    """Build a minimal asset directory and return (asset_dir, asset)."""
    asset_dir = tmp_path / "avatar"
    asset_dir.mkdir()

    # Write base.png (32, 64) indexed
    _indexed_png(asset_dir / "base.png", base_indices, palette)

    # Write eyes sheet
    sw_e, sh_e = eyes_variants[0].shape[1], eyes_variants[0].shape[0]
    eyes_arr = np.concatenate(eyes_variants, axis=1)  # horizontal strip
    _indexed_png(asset_dir / "eyes_sheet.png", eyes_arr, palette)

    # Write mouth sheet
    sw_m, sh_m = mouth_variants[0].shape[1], mouth_variants[0].shape[0]
    mouth_arr = np.concatenate(mouth_variants, axis=1)
    _indexed_png(asset_dir / "mouth_sheet.png", mouth_arr, palette)

    eye_names = [f"v{i}" for i in range(len(eyes_variants))]
    mouth_names = [f"v{i}" for i in range(len(mouth_variants))]

    asset = AvatarAsset(
        version=SCHEMA_VERSION,
        source_session="test",
        palette=palette,
        base=BaseLayerSpec(file="base.png"),
        features={
            "eyes": SpriteSheetSpec(
                sheet="eyes_sheet.png",
                sprite_size=(sw_e, sh_e),
                anchor=(10, 8),
                variants=eye_names,
            ),
            "mouth": SpriteSheetSpec(
                sheet="mouth_sheet.png",
                sprite_size=(sw_m, sh_m),
                anchor=(12, 20),
                variants=mouth_names,
            ),
        },
    )
    asset.save(asset_dir)
    return asset_dir, asset


def _simple_base() -> np.ndarray:
    """32×64 base filled with index 3 (BLACK)."""
    return np.full((32, 64), 3, dtype=np.uint8)


def _solid_sprite(w: int, h: int, idx: int) -> np.ndarray:
    return np.full((h, w), idx, dtype=np.uint8)


# ------------------------------------------------------------------ #
# Player construction                                                 #
# ------------------------------------------------------------------ #


class TestAvatarPlayerConstruction:
    def test_default_state_is_first_variant(self, tmp_path):
        base = _simple_base()
        eye_v0 = _solid_sprite(8, 3, 0)
        mouth_v0 = _solid_sprite(10, 4, 1)
        asset_dir, asset = _make_asset_dir(tmp_path, base, [eye_v0], [mouth_v0])
        player = AvatarPlayer(asset, asset_dir)
        state = player.current_state()
        assert state["eyes"] == "v0"
        assert state["mouth"] == "v0"

    def test_render_frame_returns_4096_bytes(self, tmp_path):
        base = _simple_base()
        asset_dir, asset = _make_asset_dir(
            tmp_path, base, [_solid_sprite(8, 3, 0)], [_solid_sprite(10, 4, 1)]
        )
        player = AvatarPlayer(asset, asset_dir)
        frame = player.render_frame()
        assert len(frame) == 64 * 32 * 2  # 4096 bytes, 2 bytes per pixel


# ------------------------------------------------------------------ #
# set_state / current_state                                          #
# ------------------------------------------------------------------ #


class TestSetState:
    def test_set_state_changes_variant(self, tmp_path):
        base = _simple_base()
        eyes = [_solid_sprite(8, 3, i % 4) for i in range(3)]
        asset_dir, asset = _make_asset_dir(tmp_path, base, eyes, [_solid_sprite(10, 4, 0)])
        player = AvatarPlayer(asset, asset_dir)
        player.set_state("eyes", "v2")
        assert player.current_state()["eyes"] == "v2"

    def test_set_state_unknown_feature_raises(self, tmp_path):
        base = _simple_base()
        asset_dir, asset = _make_asset_dir(
            tmp_path, base, [_solid_sprite(8, 3, 0)], [_solid_sprite(10, 4, 0)]
        )
        player = AvatarPlayer(asset, asset_dir)
        with pytest.raises(KeyError, match="nose"):
            player.set_state("nose", "v0")

    def test_set_state_unknown_variant_raises(self, tmp_path):
        base = _simple_base()
        asset_dir, asset = _make_asset_dir(
            tmp_path, base, [_solid_sprite(8, 3, 0)], [_solid_sprite(10, 4, 0)]
        )
        player = AvatarPlayer(asset, asset_dir)
        with pytest.raises(KeyError, match="squint"):
            player.set_state("eyes", "squint")


# ------------------------------------------------------------------ #
# Compositing correctness                                             #
# ------------------------------------------------------------------ #


def _decode_rgb565_to_rgb(frame_bytes: bytes, w: int = 64, h: int = 32) -> np.ndarray:
    """Decode RGB565 bytes → (h, w, 3) uint8 RGB."""
    raw = np.frombuffer(frame_bytes, dtype="<u2").reshape((h, w))
    r = ((raw >> 11) & 0x1F) << 3
    g = ((raw >> 5) & 0x3F) << 2
    b = (raw & 0x1F) << 3
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


class TestCompositing:
    def test_base_only_frame_matches_base_palette(self, tmp_path):
        """With no feature regions touching pixel (0,0), it reads the base colour."""
        # Base filled with index 0 → RED
        base = np.zeros((32, 64), dtype=np.uint8)
        # Sprites anchored far away from (0,0)
        asset_dir, asset = _make_asset_dir(
            tmp_path,
            base,
            eyes_variants=[_solid_sprite(2, 1, 1)],
            mouth_variants=[_solid_sprite(2, 1, 2)],
        )
        # Override anchors to be off-screen
        asset.features["eyes"] = SpriteSheetSpec(
            sheet="eyes_sheet.png",
            sprite_size=(2, 1),
            anchor=(100, 100),  # off the 64×32 canvas
            variants=["v0"],
        )
        asset.features["mouth"] = SpriteSheetSpec(
            sheet="mouth_sheet.png",
            sprite_size=(2, 1),
            anchor=(100, 100),
            variants=["v0"],
        )
        asset.save(asset_dir)
        player = AvatarPlayer(asset, asset_dir)
        rgb = _decode_rgb565_to_rgb(player.render_frame())

        # Pixel (0,0) should be palette[0] = RED
        # RGB565 quantisation loses low bits; check within tolerance
        assert rgb[0, 0, 0] > 200  # red channel high
        assert rgb[0, 0, 1] < 30  # green low
        assert rgb[0, 0, 2] < 30  # blue low

    def test_sprite_overwrites_base_at_anchor(self, tmp_path):
        """A GREEN sprite at anchor (0, 0) should make pixels (0,0) green."""
        base = np.zeros((32, 64), dtype=np.uint8)  # all RED (index 0)
        eye_sprite = np.ones((3, 8), dtype=np.uint8)  # all GREEN (index 1)

        asset_dir, asset = _make_asset_dir(
            tmp_path,
            base,
            eyes_variants=[eye_sprite],
            mouth_variants=[_solid_sprite(4, 2, 3)],
        )
        # Move eyes anchor to (0, 0)
        asset.features["eyes"] = SpriteSheetSpec(
            sheet="eyes_sheet.png",
            sprite_size=(8, 3),
            anchor=(0, 0),
            variants=["v0"],
        )
        asset.save(asset_dir)
        player = AvatarPlayer(asset, asset_dir)
        rgb = _decode_rgb565_to_rgb(player.render_frame())

        # Pixel (0,0) is inside the GREEN eye sprite
        assert rgb[0, 0, 1] > 200  # green channel high
        assert rgb[0, 0, 0] < 30  # red low

    def test_switching_variant_changes_output(self, tmp_path):
        """After set_state, the rendered frame should reflect the new variant."""
        base = np.full((32, 64), 3, dtype=np.uint8)  # BLACK
        eye_v0 = np.zeros((3, 8), dtype=np.uint8)  # RED
        eye_v1 = np.ones((3, 8), dtype=np.uint8)  # GREEN
        asset_dir, asset = _make_asset_dir(
            tmp_path,
            base,
            eyes_variants=[eye_v0, eye_v1],
            mouth_variants=[_solid_sprite(4, 2, 3)],
        )
        asset.features["eyes"] = SpriteSheetSpec(
            sheet="eyes_sheet.png",
            sprite_size=(8, 3),
            anchor=(0, 0),
            variants=["v0", "v1"],
        )
        asset.save(asset_dir)
        player = AvatarPlayer(asset, asset_dir)

        frame_v0 = _decode_rgb565_to_rgb(player.render_frame())
        player.set_state("eyes", "v1")
        frame_v1 = _decode_rgb565_to_rgb(player.render_frame())

        # v0 → RED at (0,0), v1 → GREEN at (0,0)
        assert frame_v0[0, 0, 0] > 200  # red
        assert frame_v1[0, 0, 1] > 200  # green
        assert not np.array_equal(frame_v0, frame_v1)
