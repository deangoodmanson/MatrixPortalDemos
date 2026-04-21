"""Schema for avatar asset bundles.

An avatar bundle is a self-contained directory produced by the avatar
builder and consumed by the player:

    asset_dir/
    ├── avatar.yaml             # serialized AvatarAsset (this file's root)
    ├── base.png                # 64×32 indexed base layer
    ├── <feature>_sheet.png     # horizontal strip of sprite variants
    └── overlays/               # optional
        └── *.png

Design contract (locked — do not change without bumping SCHEMA_VERSION):

* **Palette** is a list of 4-16 RGB888 hex strings. Indexing is positional:
  palette[0] is palette index 0 in the PNGs. The builder converts to RGB565
  at render time; the stored form is RGB888 for human readability.

* **PNG layers** use indexed-color mode ("P"). A `tRNS` chunk on sprite
  sheets and overlays marks one palette index as transparent (default: 0).
  The base layer has no transparency — it fills the full 64×32 canvas.

* **Feature sprite sheets** are horizontal strips of equal-width sprites,
  one sprite per variant. `variants` lists the variant names in sheet
  order, so sheet pixel column `i * sprite_size[0]` begins
  `variants[i]`. Standard feature names drivers expect are `eyes` and
  `mouth`; others (e.g. `brows`) are permitted and ignored by default
  drivers.

* **Anchors** are `(x, y)` top-left positions on the base canvas, same
  coordinate system as PIL (origin top-left, y grows down).

* **Overlays** are drawn last, in declared order, over everything else.

* **State machine / driver logic lives in code, not in this schema.** The
  schema describes what variants exist; drivers decide which to show.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION: int = 1

MIN_PALETTE_COLORS: int = 4
MAX_PALETTE_COLORS: int = 16

BASE_WIDTH: int = 64
BASE_HEIGHT: int = 32


@dataclass(frozen=True)
class PaletteColor:
    """One palette entry as an RGB888 triple.

    Frozen so it can serve as a dict key or set member. Use `from_hex`
    to parse `#RRGGBB` strings and `to_hex` to serialize.
    """

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for name, value in (("r", self.r), ("g", self.g), ("b", self.b)):
            if not 0 <= value <= 255:
                raise ValueError(f"Palette channel {name}={value} out of range 0-255")

    @classmethod
    def from_hex(cls, s: str) -> PaletteColor:
        """Parse a `#RRGGBB` or `RRGGBB` hex string into a PaletteColor."""
        stripped = s.lstrip("#")
        if len(stripped) != 6:
            raise ValueError(f"Invalid hex color {s!r}: expected #RRGGBB")
        try:
            r = int(stripped[0:2], 16)
            g = int(stripped[2:4], 16)
            b = int(stripped[4:6], 16)
        except ValueError as e:
            raise ValueError(f"Invalid hex color {s!r}: non-hex characters") from e
        return cls(r, g, b)

    def to_hex(self) -> str:
        """Serialize as a lowercase `#RRGGBB` hex string."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


@dataclass
class BaseLayerSpec:
    """The base 64×32 head layer: full-canvas, no transparency."""

    file: str
    size: tuple[int, int] = (BASE_WIDTH, BASE_HEIGHT)


@dataclass
class SpriteSheetSpec:
    """A feature layer stored as a horizontal strip of same-sized variants.

    The sheet PNG is `variants_count * sprite_size[0]` wide by
    `sprite_size[1]` tall. Variant `name` lives at column
    `variants.index(name) * sprite_size[0]`.
    """

    sheet: str
    sprite_size: tuple[int, int]
    anchor: tuple[int, int]
    variants: list[str]
    transparent_index: int = 0

    def __post_init__(self) -> None:
        if not self.variants:
            raise ValueError("SpriteSheetSpec.variants must not be empty")
        if len(set(self.variants)) != len(self.variants):
            raise ValueError(f"Duplicate variant names: {self.variants}")
        w, h = self.sprite_size
        if w <= 0 or h <= 0:
            raise ValueError(f"sprite_size must be positive, got {self.sprite_size}")

    def variant_index(self, name: str) -> int:
        """Return the column index of `name` within the sheet."""
        try:
            return self.variants.index(name)
        except ValueError as e:
            raise KeyError(f"Unknown variant {name!r}; have {self.variants}") from e


@dataclass
class OverlaySpec:
    """An optional overlay drawn on top of features (brows, glasses, etc.)."""

    name: str
    file: str
    anchor: tuple[int, int]
    transparent_index: int = 0


@dataclass
class AvatarAsset:
    """Root schema for one avatar bundle.

    Loaded from / saved to `<asset_dir>/avatar.yaml`. The PNG files
    referenced by `base`, `features`, and `overlays` are produced and
    consumed separately by the builder and player; this dataclass carries
    only metadata.
    """

    version: int
    source_session: str
    palette: list[PaletteColor]
    base: BaseLayerSpec
    features: dict[str, SpriteSheetSpec]
    overlays: list[OverlaySpec] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema version {self.version} (expected {SCHEMA_VERSION})"
            )
        n = len(self.palette)
        if not MIN_PALETTE_COLORS <= n <= MAX_PALETTE_COLORS:
            raise ValueError(
                f"Palette must have {MIN_PALETTE_COLORS}-{MAX_PALETTE_COLORS} colors, got {n}"
            )
        for name, spec in self.features.items():
            if not name:
                raise ValueError("Feature names must be non-empty")
            self._validate_index_in_palette(spec.transparent_index, f"feature {name!r}")
        overlay_names = [o.name for o in self.overlays]
        if len(set(overlay_names)) != len(overlay_names):
            raise ValueError(f"Duplicate overlay names: {overlay_names}")
        for o in self.overlays:
            self._validate_index_in_palette(o.transparent_index, f"overlay {o.name!r}")

    def _validate_index_in_palette(self, index: int, where: str) -> None:
        if not 0 <= index < len(self.palette):
            raise ValueError(
                f"{where}: transparent_index {index} out of palette range "
                f"0..{len(self.palette) - 1}"
            )

    @classmethod
    def load(cls, asset_dir: Path) -> AvatarAsset:
        """Load and validate an asset bundle from `<asset_dir>/avatar.yaml`.

        Raises:
            FileNotFoundError: If `avatar.yaml` is missing.
            ValueError: If the manifest is malformed or fails validation.
        """
        yaml_path = asset_dir / "avatar.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"No avatar.yaml found in {asset_dir}")
        raw = yaml.safe_load(yaml_path.read_text())
        if not isinstance(raw, dict):
            raise ValueError(f"Malformed avatar.yaml: expected mapping, got {type(raw).__name__}")
        return _from_dict(raw)

    def save(self, asset_dir: Path) -> Path:
        """Write `avatar.yaml` into `asset_dir`, creating the directory if needed.

        Returns the path to the written file. Does not touch PNG files —
        those are the builder's responsibility.
        """
        asset_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = asset_dir / "avatar.yaml"
        yaml_path.write_text(yaml.safe_dump(_to_dict(self), sort_keys=False))
        return yaml_path


def _to_dict(asset: AvatarAsset) -> dict[str, Any]:
    return {
        "version": asset.version,
        "source_session": asset.source_session,
        "metadata": dict(asset.metadata),
        "palette": [c.to_hex() for c in asset.palette],
        "base": {
            "file": asset.base.file,
            "size": list(asset.base.size),
        },
        "features": {
            name: {
                "sheet": spec.sheet,
                "sprite_size": list(spec.sprite_size),
                "anchor": list(spec.anchor),
                "variants": list(spec.variants),
                "transparent_index": spec.transparent_index,
            }
            for name, spec in asset.features.items()
        },
        "overlays": [
            {
                "name": o.name,
                "file": o.file,
                "anchor": list(o.anchor),
                "transparent_index": o.transparent_index,
            }
            for o in asset.overlays
        ],
    }


def _from_dict(raw: dict[str, Any]) -> AvatarAsset:
    try:
        palette = [PaletteColor.from_hex(c) for c in raw["palette"]]
        base_raw = raw["base"]
        base = BaseLayerSpec(
            file=base_raw["file"],
            size=_as_int_pair(base_raw.get("size", [BASE_WIDTH, BASE_HEIGHT])),
        )
        features = {
            name: SpriteSheetSpec(
                sheet=spec["sheet"],
                sprite_size=_as_int_pair(spec["sprite_size"]),
                anchor=_as_int_pair(spec["anchor"]),
                variants=list(spec["variants"]),
                transparent_index=int(spec.get("transparent_index", 0)),
            )
            for name, spec in raw.get("features", {}).items()
        }
        overlays = [
            OverlaySpec(
                name=o["name"],
                file=o["file"],
                anchor=_as_int_pair(o["anchor"]),
                transparent_index=int(o.get("transparent_index", 0)),
            )
            for o in raw.get("overlays", [])
        ]
        metadata = {str(k): str(v) for k, v in (raw.get("metadata") or {}).items()}
    except KeyError as e:
        raise ValueError(f"Missing required field in avatar.yaml: {e.args[0]!r}") from e

    return AvatarAsset(
        version=int(raw["version"]),
        source_session=str(raw["source_session"]),
        palette=palette,
        base=base,
        features=features,
        overlays=overlays,
        metadata=metadata,
    )


def _as_int_pair(value: Any) -> tuple[int, int]:
    """Coerce a 2-element sequence into `(int, int)`."""
    seq = list(value)
    if len(seq) != 2:
        raise ValueError(f"Expected 2-element sequence, got {value!r}")
    return int(seq[0]), int(seq[1])
