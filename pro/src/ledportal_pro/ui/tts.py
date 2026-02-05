"""Text-to-speech support for voice prompts.

This module provides cross-platform text-to-speech functionality using:
- macOS: Built-in 'say' command with Zarvox voice (robot)
- Linux: espeak-ng with robotic settings
- Windows: pyttsx3 library

ADVANCED CONCEPT: External Process Execution
============================================
This module demonstrates running external programs from Python using
the subprocess module. This is useful for integrating with system tools
that aren't available as Python libraries.
"""

import platform
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def speak(text: str) -> None:
    """Speak text aloud using text-to-speech.

    Uses platform-appropriate TTS engine:
    - macOS: 'say' command with Zarvox voice
    - Linux: espeak-ng with robotic settings
    - Windows: pyttsx3 library

    Silently fails if TTS is unavailable (no error raised).

    Args:
        text: The text to speak.
    """
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            # Zarvox is a classic robot voice built into macOS
            subprocess.run(["say", "-v", "Zarvox", text], check=False)

        elif system == "Linux":
            # espeak-ng with robotic settings
            # Install with: sudo apt install espeak-ng
            subprocess.run(
                ["espeak-ng", "-v", "en+m3", "-s", "130", "-p", "30", text],
                check=False,
                stderr=subprocess.DEVNULL,
            )

        else:  # Windows
            try:
                import pyttsx3

                engine = pyttsx3.init()
                engine.setProperty("rate", 130)
                engine.say(text)
                engine.runAndWait()
            except ImportError:
                pass  # pyttsx3 not installed

    except FileNotFoundError:
        # TTS program not installed
        pass
    except Exception:
        # Any other error, continue without voice
        pass


def speak_async(text: str) -> subprocess.Popen | None:
    """Speak text aloud asynchronously (non-blocking).

    Returns immediately while speech plays in background.
    Useful when you don't want to block the main loop.

    Args:
        text: The text to speak.

    Returns:
        Popen object if started successfully, None otherwise.
    """
    system = platform.system()

    try:
        if system == "Darwin":
            return subprocess.Popen(
                ["say", "-v", "Zarvox", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif system == "Linux":
            return subprocess.Popen(
                ["espeak-ng", "-v", "en+m3", "-s", "130", "-p", "30", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return None
