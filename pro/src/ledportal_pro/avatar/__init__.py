"""Avatar asset schema and pipeline.

This subpackage produces and consumes avatar bundles: palette-quantized
sprite assets generated from captured pose sessions. See `schema.py` for
the on-disk contract, `builder.py` for the build pipeline, and
`player.py` for the compositor.
"""

from .builder import build_avatar, default_model_path, download_model
from .drivers import Driver, DriverState
from .loop import AvatarLoop, BlinkFilter
from .player import AvatarPlayer
from .resolver import VariantResolver
from .schema import (
    AvatarAsset,
    BaseLayerSpec,
    OverlaySpec,
    PaletteColor,
    SpriteSheetSpec,
)

__all__ = [
    "AvatarAsset",
    "AvatarLoop",
    "AvatarPlayer",
    "BaseLayerSpec",
    "BlinkFilter",
    "Driver",
    "DriverState",
    "OverlaySpec",
    "PaletteColor",
    "SpriteSheetSpec",
    "VariantResolver",
    "build_avatar",
    "default_model_path",
    "download_model",
]
