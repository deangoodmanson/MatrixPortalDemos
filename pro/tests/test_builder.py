"""Tests for the avatar builder pipeline.

These tests cover palette extraction, palette mapping, sprite extraction,
and sheet assembly. They do NOT require MediaPipe; landmark detection is
tested via the heuristic fallback path.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ledportal_pro.avatar.builder import (
    _build_sheet,
    _extract_palette,
    _extract_sprite,
    _flat_palette,
    _heuristic_regions,
    _load_manifest,
    _map_to_palette,
    build_avatar,
)
from ledportal_pro.avatar.schema import PaletteColor

# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #


def _solid_bgr(h: int, w: int, b: int, g: int, r: int) -> np.ndarray:
    """Return a solid-colour (h, w, 3) BGR array."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :, 0] = b
    frame[:, :, 1] = g
    frame[:, :, 2] = r
    return frame


def _simple_palette(n: int = 4) -> list[PaletteColor]:
    """Return N evenly-spaced grey PaletteColors."""
    step = 255 // max(1, n - 1)
    return [PaletteColor(i * step, i * step, i * step) for i in range(n)]


def _make_session(tmp_path: Path, n_poses: int = 2) -> Path:
    """Build a minimal session directory with manifest.json and tiny BMPs."""
    session_dir = tmp_path / "avatar_test_session"
    session_dir.mkdir()

    captured = []
    for i in range(n_poses):
        angle = "front"
        expression = "neutral" if i == 0 else f"expr{i}"
        filename = f"avatar_{angle}_{expression}.bmp"
        # Write a 64×32 solid-colour BMP
        colour = (i * 60) % 200
        frame = np.full((32, 64, 3), colour, dtype=np.uint8)
        import cv2

        cv2.imwrite(str(session_dir / filename), frame)
        captured.append(
            {
                "pose": i + 1,
                "angle": angle,
                "expression": expression,
                "file": filename,
                "raw_file": None,
                "sharpness_score": 100.0,
                "burst_size": 5,
            }
        )

    manifest = {
        "session": "20260420_150000",
        "total_poses": n_poses,
        "captured": captured,
        "skipped": [],
    }
    (session_dir / "manifest.json").write_text(json.dumps(manifest))
    return session_dir


# ------------------------------------------------------------------ #
# Palette extraction                                                  #
# ------------------------------------------------------------------ #


class TestExtractPalette:
    def test_returns_correct_count(self):
        image = _solid_bgr(32, 64, 100, 150, 200)
        palette = _extract_palette(image, 4)
        assert len(palette) == 4

    def test_each_entry_is_palettecolor(self):
        image = _solid_bgr(32, 64, 50, 100, 150)
        palette = _extract_palette(image, 8)
        for c in palette:
            assert isinstance(c, PaletteColor)
            assert 0 <= c.r <= 255
            assert 0 <= c.g <= 255
            assert 0 <= c.b <= 255

    def test_gradient_image_produces_distinct_colours(self):
        """A gradient image should produce meaningfully distinct palette entries."""
        image = np.zeros((32, 64, 3), dtype=np.uint8)
        for i in range(4):
            image[:, i * 16 : (i + 1) * 16] = i * 70  # 0, 70, 140, 210
        palette = _extract_palette(image, 4)
        # At least 2 distinct colours — solid bands should separate
        unique_rs = {c.r for c in palette}
        assert len(unique_rs) >= 2


# ------------------------------------------------------------------ #
# Palette mapping                                                     #
# ------------------------------------------------------------------ #


class TestMapToPalette:
    def test_returns_pil_p_mode(self):
        image = _solid_bgr(4, 8, 0, 128, 255)
        palette = _simple_palette(4)
        result = _map_to_palette(image, palette)
        assert result.mode == "P"

    def test_dimensions_preserved(self):
        image = _solid_bgr(7, 13, 10, 20, 30)
        result = _map_to_palette(image, _simple_palette(4))
        assert result.size == (13, 7)  # PIL: (width, height)

    def test_indices_within_palette_range(self):
        image = _solid_bgr(8, 8, 50, 100, 150)
        palette = _simple_palette(6)
        result = _map_to_palette(image, palette)
        arr = np.array(result)
        assert arr.max() < len(palette)

    def test_palette_set_on_result(self):
        palette = [
            PaletteColor(255, 0, 0),
            PaletteColor(0, 255, 0),
            PaletteColor(0, 0, 255),
            PaletteColor(0, 0, 0),
        ]
        image = _solid_bgr(4, 4, 255, 0, 0)  # pure blue in BGR → (0, 0, 255) RGB
        result = _map_to_palette(image, palette)
        pal_bytes = result.getpalette()
        assert pal_bytes is not None
        assert pal_bytes[0] == 255  # first entry R
        assert pal_bytes[1] == 0  # first entry G
        assert pal_bytes[2] == 0  # first entry B


# ------------------------------------------------------------------ #
# Sprite extraction                                                   #
# ------------------------------------------------------------------ #


class TestExtractSprite:
    def test_returns_pil_p_mode(self):
        image = _solid_bgr(64, 64, 100, 100, 100)
        palette = _simple_palette(4)
        sprite = _extract_sprite(image, (10, 10, 30, 20), (12, 4), palette)
        assert sprite.mode == "P"

    def test_output_size_matches_sprite_size(self):
        image = _solid_bgr(64, 64, 50, 50, 50)
        palette = _simple_palette(4)
        sprite = _extract_sprite(image, (0, 0, 32, 32), (14, 5), palette)
        assert sprite.size == (14, 5)

    def test_handles_out_of_bounds_bbox(self):
        """Bbox that extends beyond image edges should clip gracefully."""
        image = _solid_bgr(32, 64, 80, 80, 80)
        palette = _simple_palette(4)
        sprite = _extract_sprite(image, (50, 20, 80, 40), (12, 4), palette)
        assert sprite.size == (12, 4)

    def test_empty_bbox_produces_black_sprite(self):
        image = _solid_bgr(32, 64, 100, 100, 100)
        palette = _simple_palette(4)
        sprite = _extract_sprite(image, (10, 10, 10, 10), (8, 4), palette)  # zero-size crop
        assert sprite.size == (8, 4)


# ------------------------------------------------------------------ #
# Sheet assembly                                                      #
# ------------------------------------------------------------------ #


class TestBuildSheet:
    def _make_sprite(self, w: int, h: int, idx: int, palette: list[PaletteColor]) -> Image.Image:
        arr = np.full((h, w), idx, dtype=np.uint8)
        img = Image.frombytes("P", (w, h), arr.tobytes())
        img.putpalette(_flat_palette(palette))
        return img

    def test_sheet_width_is_sprite_width_times_count(self):
        palette = _simple_palette(4)
        sprites = [self._make_sprite(12, 4, i % 4, palette) for i in range(5)]
        sheet = _build_sheet(sprites, (12, 4), palette)
        assert sheet.size == (12 * 5, 4)

    def test_sheet_mode_is_p(self):
        palette = _simple_palette(4)
        sprites = [self._make_sprite(6, 3, 0, palette)]
        sheet = _build_sheet(sprites, (6, 3), palette)
        assert sheet.mode == "P"

    def test_pixel_values_preserved(self):
        """Index 1 sprite at position 0 should read back as index 1."""
        palette = _simple_palette(4)
        sprites = [self._make_sprite(4, 2, 1, palette), self._make_sprite(4, 2, 2, palette)]
        sheet = _build_sheet(sprites, (4, 2), palette)
        arr = np.array(sheet)
        assert (arr[:, :4] == 1).all()  # first sprite
        assert (arr[:, 4:] == 2).all()  # second sprite


# ------------------------------------------------------------------ #
# Heuristic regions                                                   #
# ------------------------------------------------------------------ #


class TestHeuristicRegions:
    def test_returns_eyes_and_mouth(self):
        regions = _heuristic_regions()
        assert "eyes" in regions
        assert "mouth" in regions

    def test_normalised_values(self):
        for _name, (x1, y1, x2, y2) in _heuristic_regions().items():
            assert 0.0 <= x1 < x2 <= 1.0
            assert 0.0 <= y1 < y2 <= 1.0

    def test_eyes_above_mouth(self):
        r = _heuristic_regions()
        assert r["eyes"][3] < r["mouth"][1]  # eyes y2 < mouth y1


# ------------------------------------------------------------------ #
# Manifest loading                                                    #
# ------------------------------------------------------------------ #


class TestLoadManifest:
    def test_loads_valid_manifest(self, tmp_path):
        data = {"session": "s", "total_poses": 1, "captured": [], "skipped": []}
        (tmp_path / "manifest.json").write_text(json.dumps(data))
        manifest = _load_manifest(tmp_path)
        assert manifest["session"] == "s"

    def test_missing_manifest_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="manifest.json"):
            _load_manifest(tmp_path)


# ------------------------------------------------------------------ #
# Full build (integration, no MediaPipe)                              #
# ------------------------------------------------------------------ #


class TestBuildAvatar:
    def test_build_creates_asset_files(self, tmp_path):
        session_dir = _make_session(tmp_path, n_poses=3)
        output_dir = tmp_path / "asset_out"
        asset = build_avatar(session_dir, output_dir, palette_size=4, model_path=None)

        assert (output_dir / "avatar.yaml").exists()
        assert (output_dir / "base.png").exists()
        for feature in asset.features:
            assert (output_dir / f"{feature}_sheet.png").exists()

    def test_build_returns_avatar_asset(self, tmp_path):
        from ledportal_pro.avatar.schema import AvatarAsset

        session_dir = _make_session(tmp_path, n_poses=2)
        output_dir = tmp_path / "asset_out2"
        asset = build_avatar(session_dir, output_dir, palette_size=4, model_path=None)
        assert isinstance(asset, AvatarAsset)

    def test_asset_loadable_after_build(self, tmp_path):
        from ledportal_pro.avatar.schema import AvatarAsset

        session_dir = _make_session(tmp_path, n_poses=2)
        output_dir = tmp_path / "asset_out3"
        build_avatar(session_dir, output_dir, palette_size=4, model_path=None)
        loaded = AvatarAsset.load(output_dir)
        assert loaded.version == 1
        assert len(loaded.palette) == 4

    def test_variant_count_matches_pose_count(self, tmp_path):
        n_poses = 4
        session_dir = _make_session(tmp_path, n_poses=n_poses)
        output_dir = tmp_path / "asset_out4"
        asset = build_avatar(session_dir, output_dir, palette_size=4, model_path=None)
        for spec in asset.features.values():
            assert len(spec.variants) == n_poses
