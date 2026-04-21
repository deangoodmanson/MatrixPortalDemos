"""Variant resolver: maps semantic DriverState to concrete variant names.

The resolver knows one thing the rest of the system does not: how capture
filenames encode semantics. Variant names follow the pattern
``{angle}_{expression}`` (e.g. ``front_neutral``, ``left_eyes_closed``).

At construction the resolver builds two indexes from the asset:
- ``_eye_index[(angle, eye_sem)]  → variant_name``
- ``_mouth_index[(angle, mouth_sem)] → variant_name``

``resolve()`` accepts a DriverState and returns only the features whose
resolved variant changed — so ``AvatarPlayer.set_state`` is never called
redundantly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .drivers import DriverState
from .schema import AvatarAsset

# Maps each capture expression name to (eye_semantic, mouth_semantic).
# Eye semantics: "open" | "closed" | "raised" | "furrowed"
# Mouth semantics: "neutral" | "smile" | "smile_open" | "o" | "ee" | "closed"
_EXPRESSION_SEMANTICS: dict[str, tuple[str, str]] = {
    "neutral": ("open", "neutral"),
    "smile": ("open", "smile"),
    "smile_open": ("open", "smile_open"),
    "eyebrows_up": ("raised", "neutral"),
    "eyes_closed": ("closed", "neutral"),
    "mouth_o": ("open", "o"),
    "mouth_ee": ("open", "ee"),
    "mouth_closed": ("open", "closed"),
    "furrowed": ("furrowed", "neutral"),
}

# Valid angle names.
_ANGLES = frozenset({"front", "left", "right", "up", "down"})


@dataclass
class _ResolvedSemantics:
    """Internal tracking of the last fully-resolved semantic state."""

    angle: str = "front"
    eyes: str = "open"
    mouth: str = "neutral"


class VariantResolver:
    """Resolves semantic DriverState into concrete variant names for each feature.

    Args:
        asset: The loaded AvatarAsset providing variant names.

    Example::

        resolver = VariantResolver(asset)
        changes = resolver.resolve(DriverState(eyes="closed"))
        # → {"eyes": "front_eyes_closed"} or nearest fallback
    """

    def __init__(self, asset: AvatarAsset) -> None:
        self._variants: list[str] = []
        self._eye_index: dict[tuple[str, str], str] = {}
        self._mouth_index: dict[tuple[str, str], str] = {}

        # Collect all variant names across all features.
        for spec in asset.features.values():
            self._variants.extend(spec.variants)

        self._build_indexes(asset)
        self._last = _ResolvedSemantics()
        self._last_output: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def resolve(self, state: DriverState) -> dict[str, str]:
        """Merge ``state`` with the last resolved semantics and look up variants.

        Only features whose resolved variant changed are returned, so callers
        can pass the result straight to ``AvatarPlayer.set_state`` without
        redundant updates.

        Args:
            state: Incoming driver state (any field may be None).

        Returns:
            ``{"eyes": variant_name, "mouth": variant_name}`` for any feature
            whose resolved variant differs from the previous call.
        """
        if state.angle is not None and state.angle in _ANGLES:
            self._last.angle = state.angle
        if state.eyes is not None:
            self._last.eyes = state.eyes
        if state.mouth is not None:
            self._last.mouth = state.mouth

        changes: dict[str, str] = {}

        eye_variant = self._lookup_eye(self._last.angle, self._last.eyes)
        if self._last_output.get("eyes") != eye_variant:
            changes["eyes"] = eye_variant
            self._last_output["eyes"] = eye_variant

        mouth_variant = self._lookup_mouth(self._last.angle, self._last.mouth)
        if self._last_output.get("mouth") != mouth_variant:
            changes["mouth"] = mouth_variant
            self._last_output["mouth"] = mouth_variant

        return changes

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _build_indexes(self, asset: AvatarAsset) -> None:
        """Populate ``_eye_index`` and ``_mouth_index`` from asset variants."""
        all_variants: list[str] = []
        for spec in asset.features.values():
            all_variants.extend(spec.variants)

        for variant in all_variants:
            parts = variant.split("_", 1)
            if len(parts) != 2:
                continue
            angle, expression = parts
            semantics = _EXPRESSION_SEMANTICS.get(expression)
            if semantics is None:
                continue
            eye_sem, mouth_sem = semantics

            key_eye = (angle, eye_sem)
            if key_eye not in self._eye_index:
                self._eye_index[key_eye] = variant

            key_mouth = (angle, mouth_sem)
            if key_mouth not in self._mouth_index:
                self._mouth_index[key_mouth] = variant

    def _lookup_eye(self, angle: str, sem: str) -> str:
        """Find the best eye variant for the given angle and semantic.

        Fallback chain:
        1. Exact (angle, sem).
        2. ("front", sem).
        3. Any variant with that semantic (any angle).
        4. First variant in the asset.
        """
        if v := self._eye_index.get((angle, sem)):
            return v
        if v := self._eye_index.get(("front", sem)):
            return v
        for (_, s), v in self._eye_index.items():
            if s == sem:
                return v
        return self._variants[0] if self._variants else ""

    def _lookup_mouth(self, angle: str, sem: str) -> str:
        """Find the best mouth variant for the given angle and semantic.

        Same four-tier fallback chain as ``_lookup_eye``.
        """
        if v := self._mouth_index.get((angle, sem)):
            return v
        if v := self._mouth_index.get(("front", sem)):
            return v
        for (_, s), v in self._mouth_index.items():
            if s == sem:
                return v
        return self._variants[0] if self._variants else ""
