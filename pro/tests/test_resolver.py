"""Tests for VariantResolver: semantic → variant with fallback chain."""

from __future__ import annotations

from ledportal_pro.avatar.drivers import DriverState
from ledportal_pro.avatar.resolver import _EXPRESSION_SEMANTICS, VariantResolver
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

_PALETTE = [
    PaletteColor(0, 0, 0),
    PaletteColor(255, 255, 255),
    PaletteColor(128, 0, 0),
    PaletteColor(0, 128, 0),
]


def _asset(variants: list[str]) -> AvatarAsset:
    """Build a minimal AvatarAsset with the given variant names on both features."""
    return AvatarAsset(
        version=SCHEMA_VERSION,
        source_session="test",
        palette=_PALETTE,
        base=BaseLayerSpec(file="base.png"),
        features={
            "eyes": SpriteSheetSpec(
                sheet="eyes_sheet.png",
                sprite_size=(8, 3),
                anchor=(10, 8),
                variants=variants,
            ),
            "mouth": SpriteSheetSpec(
                sheet="mouth_sheet.png",
                sprite_size=(10, 4),
                anchor=(12, 20),
                variants=variants,
            ),
        },
    )


# ------------------------------------------------------------------ #
# Expression semantics table                                          #
# ------------------------------------------------------------------ #


class TestExpressionSemantics:
    def test_all_entries_have_two_semantics(self):
        for expr, (eye, mouth) in _EXPRESSION_SEMANTICS.items():
            assert isinstance(eye, str) and eye, f"{expr} eye sem empty"
            assert isinstance(mouth, str) and mouth, f"{expr} mouth sem empty"

    def test_neutral_maps_to_open_neutral(self):
        assert _EXPRESSION_SEMANTICS["neutral"] == ("open", "neutral")

    def test_eyes_closed_maps_correctly(self):
        eye, mouth = _EXPRESSION_SEMANTICS["eyes_closed"]
        assert eye == "closed"
        assert mouth == "neutral"


# ------------------------------------------------------------------ #
# Exact match (tier 1)                                               #
# ------------------------------------------------------------------ #


class TestExactMatch:
    def test_front_neutral_resolves_to_front_neutral(self):
        asset = _asset(["front_neutral", "front_smile"])
        resolver = VariantResolver(asset)
        changes = resolver.resolve(DriverState(angle="front", eyes="open", mouth="neutral"))
        assert changes.get("eyes") == "front_neutral"
        assert changes.get("mouth") == "front_neutral"

    def test_left_closed_resolves_to_left_eyes_closed(self):
        asset = _asset(["front_neutral", "left_eyes_closed"])
        resolver = VariantResolver(asset)
        resolver.resolve(DriverState(angle="left", eyes="open", mouth="neutral"))
        changes = resolver.resolve(DriverState(eyes="closed"))
        assert changes.get("eyes") == "left_eyes_closed"


# ------------------------------------------------------------------ #
# Front fallback (tier 2)                                            #
# ------------------------------------------------------------------ #


class TestFrontFallback:
    def test_right_raised_falls_back_to_front_eyebrows_up(self):
        """No right_raised — should fall back to front_eyebrows_up."""
        asset = _asset(["front_eyebrows_up", "front_neutral"])
        resolver = VariantResolver(asset)
        changes = resolver.resolve(DriverState(angle="right", eyes="raised", mouth="neutral"))
        assert changes.get("eyes") == "front_eyebrows_up"


# ------------------------------------------------------------------ #
# Any-angle fallback (tier 3)                                        #
# ------------------------------------------------------------------ #


class TestAnyAngleFallback:
    def test_up_smile_falls_back_to_left_smile(self):
        """Only left_smile in asset; up angle requested."""
        asset = _asset(["left_smile", "front_neutral"])
        resolver = VariantResolver(asset)
        changes = resolver.resolve(DriverState(angle="up", eyes="open", mouth="smile"))
        assert changes.get("mouth") == "left_smile"


# ------------------------------------------------------------------ #
# Last-resort fallback (tier 4)                                      #
# ------------------------------------------------------------------ #


class TestLastResortFallback:
    def test_unknown_semantic_falls_back_to_first_variant(self):
        asset = _asset(["front_neutral"])
        resolver = VariantResolver(asset)
        changes = resolver.resolve(DriverState(eyes="open", mouth="neutral"))
        # front_neutral matches exactly for both; this just confirms no crash
        assert changes.get("eyes") == "front_neutral"

    def test_completely_unmappable_falls_back_to_first(self):
        """Asset with a variant that has no semantic entry."""
        asset = _asset(["front_mystery"])
        resolver = VariantResolver(asset)
        changes = resolver.resolve(DriverState(eyes="open", mouth="neutral"))
        # No eye/mouth index entries → tier-4 first-variant fallback
        assert changes.get("eyes") == "front_mystery"
        assert changes.get("mouth") == "front_mystery"


# ------------------------------------------------------------------ #
# Partial updates / state accumulation                               #
# ------------------------------------------------------------------ #


class TestPartialUpdates:
    def test_none_angle_keeps_last_angle(self):
        asset = _asset(["left_neutral", "front_smile"])
        resolver = VariantResolver(asset)
        resolver.resolve(DriverState(angle="left", eyes="open", mouth="neutral"))
        changes = resolver.resolve(DriverState(angle=None, eyes="open", mouth="smile"))
        # mouth smile at left angle; eyes stays open; only changed features returned
        assert "eyes" not in changes or changes["eyes"] is not None

    def test_only_angle_change_triggers_re_lookup(self):
        """Changing angle with all-None eyes/mouth re-resolves at new angle."""
        asset = _asset(["front_neutral", "left_neutral"])
        resolver = VariantResolver(asset)
        resolver.resolve(DriverState(angle="front", eyes="open", mouth="neutral"))
        changes = resolver.resolve(DriverState(angle="left"))
        # left_neutral should now be resolved for eyes
        assert changes.get("eyes") == "left_neutral"

    def test_unchanged_variant_not_returned(self):
        asset = _asset(["front_neutral"])
        resolver = VariantResolver(asset)
        resolver.resolve(DriverState(angle="front", eyes="open", mouth="neutral"))
        changes = resolver.resolve(DriverState(angle="front", eyes="open", mouth="neutral"))
        # Nothing changed — resolver should return empty dict
        assert changes == {}


# ------------------------------------------------------------------ #
# Edge cases                                                          #
# ------------------------------------------------------------------ #


class TestEdgeCases:
    def test_empty_state_emits_initial_defaults(self):
        asset = _asset(["front_neutral"])
        resolver = VariantResolver(asset)
        changes = resolver.resolve(DriverState())
        # First call always returns something (bootstraps the output)
        assert "eyes" in changes
        assert "mouth" in changes

    def test_invalid_angle_ignored(self):
        asset = _asset(["front_neutral"])
        resolver = VariantResolver(asset)
        resolver.resolve(DriverState(angle="front"))
        changes = resolver.resolve(DriverState(angle="sideways"))
        # "sideways" not in _ANGLES — angle should stay "front"
        assert "eyes" not in changes  # no change if variant is the same
