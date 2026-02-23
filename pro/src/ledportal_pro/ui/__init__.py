"""UI module for LED Portal Pro."""

from .avatar import AVATAR_POSES, AvatarCaptureManager, AvatarSession, CapturedPose
from .input import InputCommand, KeyboardHandler, print_help
from .overlay import draw_border, draw_countdown_overlay, show_preview
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
    # Text-to-speech
    "speak",
    "speak_async",
]
