"""UI module for LED Portal Pro."""

from .avatar import AVATAR_POSES, AvatarCaptureManager, AvatarSession, CapturedPose
from .input import InputCommand, KeyboardHandler, print_help
from .overlay import draw_countdown_overlay
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
    # Text-to-speech
    "speak",
    "speak_async",
]
