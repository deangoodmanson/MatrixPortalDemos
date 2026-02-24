"""UI module for LED Portal Pro."""

from .avatar import AVATAR_POSES, AvatarCaptureManager, AvatarSession, CapturedPose
from .input import InputCommand, KeyboardHandler, print_help
from .overlay import (
    PreviewMode,
    draw_border,
    draw_countdown_overlay,
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
    # Avatar capture
    "AVATAR_POSES",
    "AvatarCaptureManager",
    "AvatarSession",
    "CapturedPose",
    # Snapshot and overlay
    "SnapshotManager",
    "draw_countdown_overlay",
    "draw_border",
    "show_preview",
    "render_led_preview",
    "PreviewMode",
    # Text-to-speech
    "speak",
    "speak_async",
]
