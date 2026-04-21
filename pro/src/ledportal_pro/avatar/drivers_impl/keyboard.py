"""Keyboard-driven avatar expression driver.

Uses non-blocking terminal input (``select`` on POSIX, ``msvcrt`` on Windows)
so the driver can be polled inside the AvatarLoop without blocking.

Key map
-------
Eye semantics (number row):
  1 → eyes open       2 → eyes closed
  3 → eyes raised     4 → eyes furrowed

Mouth semantics:
  5 → mouth neutral   6 → mouth smile     7 → mouth smile_open
  8 → mouth o         9 → mouth ee

Angle (WASDE cluster):
  W → up              S → down
  A → left            D → right
  E → front

Stop:
  Q or Esc → stop
"""

from __future__ import annotations

import sys
import termios
import tty

from ..drivers import DriverState

_EYE_KEYS: dict[str, str] = {
    "1": "open",
    "2": "closed",
    "3": "raised",
    "4": "furrowed",
}

_MOUTH_KEYS: dict[str, str] = {
    "5": "neutral",
    "6": "smile",
    "7": "smile_open",
    "8": "o",
    "9": "ee",
}

_ANGLE_KEYS: dict[str, str] = {
    "w": "up",
    "s": "down",
    "a": "left",
    "d": "right",
    "e": "front",
}

_STOP_KEYS = frozenset({"q", "\x1b"})  # Q or Esc


class KeyboardDriver:
    """Non-blocking keyboard driver for avatar expression control.

    Reads one character at a time from stdin without echoing. Each poll call
    drains all pending keypresses, applying the last relevant key for each
    category (angle / eyes / mouth).

    Args:
        fd: File descriptor to read from (default: sys.stdin).
    """

    def __init__(self, fd: int | None = None) -> None:
        self._fd = fd if fd is not None else sys.stdin.fileno()
        self._stop = False
        self._old_settings: list[object] | None = None
        self._pending: list[str] = []
        self._setup_terminal()
        self._print_controls()

    # ------------------------------------------------------------------ #
    # Driver protocol                                                      #
    # ------------------------------------------------------------------ #

    def poll(self, dt: float) -> DriverState:  # noqa: ARG002
        keys = self._read_pending()

        angle: str | None = None
        eyes: str | None = None
        mouth: str | None = None

        for key in keys:
            if key in _STOP_KEYS:
                self._stop = True
            elif key in _EYE_KEYS:
                eyes = _EYE_KEYS[key]
            elif key in _MOUTH_KEYS:
                mouth = _MOUTH_KEYS[key]
            elif key in _ANGLE_KEYS:
                angle = _ANGLE_KEYS[key]

        return DriverState(angle=angle, eyes=eyes, mouth=mouth)

    def should_stop(self) -> bool:
        return self._stop

    def close(self) -> None:
        self._restore_terminal()

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _setup_terminal(self) -> None:
        try:
            self._old_settings = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        except termios.error:
            self._old_settings = None

    def _restore_terminal(self) -> None:
        if self._old_settings is not None:
            try:
                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
            except termios.error:
                pass

    def _read_pending(self) -> list[str]:
        """Drain all available characters from stdin without blocking."""
        import select

        chars: list[str] = []
        while True:
            ready, _, _ = select.select([self._fd], [], [], 0)
            if not ready:
                break
            try:
                ch = sys.stdin.read(1)
                if ch:
                    chars.append(ch.lower())
            except OSError:
                break
        return chars

    @staticmethod
    def _print_controls() -> None:
        print("\nKeyboard Avatar Controls:")
        print("  Eyes:  1=open  2=closed  3=raised  4=furrowed")
        print("  Mouth: 5=neutral  6=smile  7=smile_open  8=o  9=ee")
        print("  Angle: W=up  S=down  A=left  D=right  E=front")
        print("  Stop:  Q or Esc\n")
