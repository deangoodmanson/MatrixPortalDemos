"""UI module for LED Portal Pro."""

from .avatar import AVATAR_POSES, AvatarCaptureManager, AvatarSession, CapturedPose
from .demo import DemoMode
from .input import InputCommand, KeyboardHandler, print_help
from .overlay import (
    _ALGORITHM_LABELS,
    LED_SIZE_DEFAULT,
    LED_SIZE_STEPS,
    PreviewAlgorithm,
    draw_border,
    draw_countdown_overlay,
    draw_text_overlay,
    render_led_preview,
    show_preview,
)
from .snapshot import SnapshotManager
from .tts import speak, speak_async

__all__ = [
    # Input handling
    "InputCommand",
    "KeyboardHandler",
    "print_help",
    # Demo mode
    "DemoMode",
    # Avatar capture
    "AVATAR_POSES",
    "AvatarCaptureManager",
    "AvatarSession",
    "CapturedPose",
    # Snapshot and overlay
    "SnapshotManager",
    "draw_countdown_overlay",
    "draw_text_overlay",
    "draw_border",
    "show_preview",
    "render_led_preview",
    "PreviewAlgorithm",
    "LED_SIZE_STEPS",
    "LED_SIZE_DEFAULT",
    "_ALGORITHM_LABELS",
    # Text-to-speech
    "speak",
    "speak_async",
]
