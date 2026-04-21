"""Tests for the avatar asset schema.

These tests lock the on-disk contract: round-trip through YAML,
validation failures, and sprite-sheet variant lookup. They do NOT
touch PNG files — the schema is metadata only.
"""

from dataclasses import FrozenInstanceError

import pytest
import yaml

from ledportal_pro.avatar.schema import (
    BASE_HEIGHT,
    BASE_WIDTH,
    MAX_PALETTE_COLORS,
    MIN_PALETTE_COLORS,
    SCHEMA_VERSION,
    AvatarAsset,
    BaseLayerSpec,
    OverlaySpec,
    PaletteColor,
    SpriteSheetSpec,
)

# -------- PaletteColor --------


class TestPaletteColor:
    def test_hex_roundtrip(self):
        for hex_in in ("#1a2b3c", "#ffffff", "#000000", "#00ff80"):
            color = PaletteColor.from_hex(hex_in)
            assert color.to_hex() == hex_in.lower()

    def test_hex_without_hash(self):
        assert PaletteColor.from_hex("abcdef") == PaletteColor(0xAB, 0xCD, 0xEF)

    def test_rejects_short_hex(self):
        with pytest.raises(ValueError, match="expected #RRGGBB"):
            PaletteColor.from_hex("#abc")

    def test_rejects_non_hex_chars(self):
        with pytest.raises(ValueError, match="non-hex"):
            PaletteColor.from_hex("#zzzzzz")

    def test_rejects_out_of_range_channels(self):
        with pytest.raises(ValueError, match="out of range"):
            PaletteColor(256, 0, 0)

    def test_frozen(self):
        c = PaletteColor(1, 2, 3)
        with pytest.raises(FrozenInstanceError):
            c.r = 99  # type: ignore[misc]

    def test_hashable(self):
        # Frozen dataclasses are hashable; exercise that.
        s = {PaletteColor(1, 2, 3), PaletteColor(1, 2, 3), PaletteColor(4, 5, 6)}
        assert len(s) == 2


# -------- SpriteSheetSpec --------


class TestSpriteSheetSpec:
    def _make(self, **kwargs):
        defaults = {
            "sheet": "eyes.png",
            "sprite_size": (12, 4),
            "anchor": (26, 10),
            "variants": ["open", "closed"],
            "transparent_index": 0,
        }
        defaults.update(kwargs)
        return SpriteSheetSpec(**defaults)

    def test_variant_index_lookup(self):
        spec = self._make(variants=["open", "closed", "left"])
        assert spec.variant_index("open") == 0
        assert spec.variant_index("left") == 2

    def test_variant_index_unknown_raises_keyerror(self):
        spec = self._make(variants=["open", "closed"])
        with pytest.raises(KeyError, match="Unknown variant"):
            spec.variant_index("squint")

    def test_empty_variants_rejected(self):
        with pytest.raises(ValueError, match="must not be empty"):
            self._make(variants=[])

    def test_duplicate_variants_rejected(self):
        with pytest.raises(ValueError, match="Duplicate variant"):
            self._make(variants=["open", "open"])

    def test_nonpositive_sprite_size_rejected(self):
        with pytest.raises(ValueError, match="must be positive"):
            self._make(sprite_size=(0, 4))


# -------- AvatarAsset construction --------


def _make_minimal_asset(**overrides):
    """Build a minimal valid AvatarAsset for tests."""
    defaults = {
        "version": SCHEMA_VERSION,
        "source_session": "avatar_20260420_150000",
        "palette": [
            PaletteColor(26, 26, 26),
            PaletteColor(244, 194, 161),
            PaletteColor(43, 43, 43),
            PaletteColor(255, 255, 255),
        ],
        "base": BaseLayerSpec(file="base.png"),
        "features": {
            "eyes": SpriteSheetSpec(
                sheet="eyes_sheet.png",
                sprite_size=(12, 4),
                anchor=(26, 10),
                variants=["open", "closed"],
            ),
            "mouth": SpriteSheetSpec(
                sheet="mouth_sheet.png",
                sprite_size=(14, 5),
                anchor=(25, 20),
                variants=["neutral", "smile", "o"],
            ),
        },
    }
    defaults.update(overrides)
    return AvatarAsset(**defaults)


class TestAvatarAssetConstruction:
    def test_minimal_valid_asset(self):
        asset = _make_minimal_asset()
        assert asset.version == SCHEMA_VERSION
        assert len(asset.palette) == 4
        assert asset.base.size == (BASE_WIDTH, BASE_HEIGHT)
        assert asset.overlays == []
        assert asset.metadata == {}

    def test_unsupported_version_rejected(self):
        with pytest.raises(ValueError, match="Unsupported schema version"):
            _make_minimal_asset(version=999)

    def test_palette_too_small_rejected(self):
        with pytest.raises(ValueError, match=f"{MIN_PALETTE_COLORS}-{MAX_PALETTE_COLORS}"):
            _make_minimal_asset(palette=[PaletteColor(0, 0, 0)])

    def test_palette_too_large_rejected(self):
        too_many = [PaletteColor(i, i, i) for i in range(MAX_PALETTE_COLORS + 1)]
        with pytest.raises(ValueError, match=f"{MIN_PALETTE_COLORS}-{MAX_PALETTE_COLORS}"):
            _make_minimal_asset(palette=too_many)

    def test_feature_transparent_index_out_of_range_rejected(self):
        features = {
            "eyes": SpriteSheetSpec(
                sheet="eyes.png",
                sprite_size=(12, 4),
                anchor=(0, 0),
                variants=["open"],
                transparent_index=99,
            )
        }
        with pytest.raises(ValueError, match="transparent_index 99 out of palette"):
            _make_minimal_asset(features=features)

    def test_duplicate_overlay_names_rejected(self):
        overlays = [
            OverlaySpec(name="brow", file="a.png", anchor=(0, 0)),
            OverlaySpec(name="brow", file="b.png", anchor=(0, 0)),
        ]
        with pytest.raises(ValueError, match="Duplicate overlay"):
            _make_minimal_asset(overlays=overlays)


# -------- YAML round-trip --------


class TestRoundTrip:
    def test_save_then_load_preserves_all_fields(self, tmp_path):
        original = _make_minimal_asset(
            overlays=[OverlaySpec(name="brow_furrow", file="overlays/brow.png", anchor=(25, 7))],
            metadata={"created_at": "2026-04-20T15:00:00", "builder_version": "0.1.0"},
        )
        original.save(tmp_path)

        loaded = AvatarAsset.load(tmp_path)

        assert loaded.version == original.version
        assert loaded.source_session == original.source_session
        assert loaded.palette == original.palette
        assert loaded.base == original.base
        assert loaded.features == original.features
        assert loaded.overlays == original.overlays
        assert loaded.metadata == original.metadata

    def test_save_creates_asset_dir(self, tmp_path):
        asset = _make_minimal_asset()
        target = tmp_path / "nested" / "avatar_foo"
        path = asset.save(target)
        assert path == target / "avatar.yaml"
        assert path.exists()

    def test_load_missing_yaml_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            AvatarAsset.load(tmp_path)

    def test_load_non_mapping_yaml_raises(self, tmp_path):
        (tmp_path / "avatar.yaml").write_text("- just\n- a\n- list\n")
        with pytest.raises(ValueError, match="expected mapping"):
            AvatarAsset.load(tmp_path)

    def test_load_missing_required_field_raises(self, tmp_path):
        # Valid YAML but missing `palette`.
        yaml_text = yaml.safe_dump(
            {
                "version": SCHEMA_VERSION,
                "source_session": "x",
                "base": {"file": "base.png"},
                "features": {},
            }
        )
        (tmp_path / "avatar.yaml").write_text(yaml_text)
        with pytest.raises(ValueError, match="Missing required field"):
            AvatarAsset.load(tmp_path)

    def test_load_unsupported_version_raises(self, tmp_path):
        asset = _make_minimal_asset()
        asset.save(tmp_path)
        # Hand-edit to bump version.
        yaml_path = tmp_path / "avatar.yaml"
        raw = yaml.safe_load(yaml_path.read_text())
        raw["version"] = 999
        yaml_path.write_text(yaml.safe_dump(raw))
        with pytest.raises(ValueError, match="Unsupported schema version"):
            AvatarAsset.load(tmp_path)

    def test_lists_round_trip_as_tuples(self, tmp_path):
        """YAML stores sequences as lists; loader must re-tuple them."""
        asset = _make_minimal_asset()
        asset.save(tmp_path)
        loaded = AvatarAsset.load(tmp_path)
        assert isinstance(loaded.base.size, tuple)
        assert isinstance(loaded.features["eyes"].sprite_size, tuple)
        assert isinstance(loaded.features["eyes"].anchor, tuple)
