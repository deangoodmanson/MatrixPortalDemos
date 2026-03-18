"""Keyboard input handling with single-keypress support."""

import select
import sys
import termios
import tty
from dataclasses import dataclass
from enum import Enum, auto
from types import TracebackType
from typing import Any


class InputCommand(Enum):
    """Enumeration of possible input commands."""

    NONE = auto()
    # Display orientation
    ORIENTATION_LANDSCAPE = auto()
    ORIENTATION_PORTRAIT = auto()
    # Processing modes
    PROCESSING_CENTER = auto()
    PROCESSING_STRETCH = auto()
    PROCESSING_FIT = auto()
    # Effects
    TOGGLE_BW = auto()
    TOGGLE_MIRROR = auto()
    ZOOM_TOGGLE = auto()
    CYCLE_RENDER_ALGORITHM = auto()
    LED_SIZE_INCREASE = auto()
    LED_SIZE_DECREASE = auto()
    # Actions
    SNAPSHOT = auto()
    AVATAR = auto()  # Avatar capture mode
    TOGGLE_DISPLAY = auto()  # Toggle transmission to matrix
    TOGGLE_DEBUG = auto()
    TOGGLE_PREVIEW = auto()  # Toggle preview window
    DEMO_TOGGLE = auto()  # Toggle automatic demo mode
    DEMO_MANUAL = auto()  # Start manual (navigate-only) demo mode
    DEMO_NEXT = auto()  # Next demo step
    DEMO_PREV = auto()  # Previous demo step
    RESET = auto()
    HELP = auto()
    QUIT = auto()
    # For snapshot abort
    ABORT = auto()


@dataclass
class InputResult:
    """Result of checking for keyboard input."""

    command: InputCommand
    raw_input: str | None = None


class KeyboardHandler:
    """Handles non-blocking keyboard input with single-keypress support.

    Use as context manager to ensure terminal is properly restored:

        with KeyboardHandler() as keyboard:
            while True:
                result = keyboard.check_input()
                ...
    """

    def __init__(self, single_keypress: bool = True) -> None:
        """Initialize keyboard handler.

        Args:
            single_keypress: If True, use cbreak mode for single-keypress input.
                           Only works on Mac/Linux. Falls back to readline on Windows.
        """
        self._enabled = True
        self._single_keypress = single_keypress
        self._old_settings: Any = None
        self._in_context = False

    def __enter__(self) -> KeyboardHandler:
        """Enter context manager, set terminal to cbreak mode."""
        self._in_context = True
        if self._single_keypress:
            try:
                self._old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except termios.error, OSError:
                # Not a terminal or not supported
                self._single_keypress = False
                self._old_settings = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, restore terminal settings."""
        self._restore_terminal()
        self._in_context = False

    def _restore_terminal(self) -> None:
        """Restore original terminal settings."""
        if self._old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
            except termios.error, OSError:
                pass
            self._old_settings = None

    def check_input(self) -> InputResult:
        """Check for keyboard input without blocking.

        Returns:
            InputResult with the detected command.
        """
        if not self._enabled:
            return InputResult(InputCommand.NONE)

        try:
            if select.select([sys.stdin], [], [], 0)[0]:
                if self._single_keypress and self._in_context:
                    # Single character read — preserve case for shift-key commands
                    raw_char = sys.stdin.read(1)
                    return self._parse_single_key(raw_char)
                else:
                    # Line-based input
                    line = sys.stdin.readline().strip().lower()
                    return self._parse_line(line)
        except OSError, ValueError:
            pass

        return InputResult(InputCommand.NONE)

    def _parse_single_key(self, char: str) -> InputResult:
        """Parse single keypress into command.

        Case-sensitive keys (checked before lowercasing):
        - X (shift+x): manual demo mode
        - >/. : demo next step
        - </,  : demo previous step

        Args:
            char: Single character input (original case preserved).

        Returns:
            InputResult with the parsed command.
        """
        # Case-sensitive keys checked first
        case_sensitive_map = {
            "X": InputCommand.DEMO_MANUAL,
            ".": InputCommand.DEMO_NEXT,
            ">": InputCommand.DEMO_NEXT,
            ",": InputCommand.DEMO_PREV,
            "<": InputCommand.DEMO_PREV,
        }
        if char in case_sensitive_map:
            return InputResult(case_sensitive_map[char], char)

        # Everything else is case-insensitive
        lower = char.lower()
        key_map = {
            # Display orientation
            "l": InputCommand.ORIENTATION_LANDSCAPE,
            "p": InputCommand.ORIENTATION_PORTRAIT,
            # Processing modes
            "c": InputCommand.PROCESSING_CENTER,
            "s": InputCommand.PROCESSING_STRETCH,
            "f": InputCommand.PROCESSING_FIT,
            # Effects
            "b": InputCommand.TOGGLE_BW,
            "m": InputCommand.TOGGLE_MIRROR,
            "z": InputCommand.ZOOM_TOGGLE,
            "o": InputCommand.CYCLE_RENDER_ALGORITHM,
            "+": InputCommand.LED_SIZE_INCREASE,
            "=": InputCommand.LED_SIZE_INCREASE,
            "-": InputCommand.LED_SIZE_DECREASE,
            "_": InputCommand.LED_SIZE_DECREASE,
            # Actions
            " ": InputCommand.SNAPSHOT,
            "v": InputCommand.AVATAR,
            "x": InputCommand.DEMO_TOGGLE,
            # System
            "t": InputCommand.TOGGLE_DISPLAY,
            "d": InputCommand.TOGGLE_DEBUG,
            "w": InputCommand.TOGGLE_PREVIEW,
            "r": InputCommand.RESET,
            "h": InputCommand.HELP,
            "q": InputCommand.QUIT,
        }

        command = key_map.get(lower, InputCommand.NONE)
        return InputResult(command, char)

    def _parse_line(self, line: str) -> InputResult:
        """Parse input line into command (fallback for non-cbreak mode).

        Args:
            line: Input line (already lowercased and stripped).

        Returns:
            InputResult with the parsed command.
        """
        if line == "":
            return InputResult(InputCommand.SNAPSHOT, line)
        elif line == "l":
            return InputResult(InputCommand.ORIENTATION_LANDSCAPE, line)
        elif line == "p":
            return InputResult(InputCommand.ORIENTATION_PORTRAIT, line)
        elif line == "c":
            return InputResult(InputCommand.PROCESSING_CENTER, line)
        elif line == "s":
            return InputResult(InputCommand.PROCESSING_STRETCH, line)
        elif line == "f":
            return InputResult(InputCommand.PROCESSING_FIT, line)
        elif line == "b":
            return InputResult(InputCommand.TOGGLE_BW, line)
        elif line == "m":
            return InputResult(InputCommand.TOGGLE_MIRROR, line)
        elif line == "z":
            return InputResult(InputCommand.ZOOM_TOGGLE, line)
        elif line == "o":
            return InputResult(InputCommand.CYCLE_RENDER_ALGORITHM, line)
        elif line in ("+", "="):
            return InputResult(InputCommand.LED_SIZE_INCREASE, line)
        elif line in ("-", "_"):
            return InputResult(InputCommand.LED_SIZE_DECREASE, line)
        elif line == "v":
            return InputResult(InputCommand.AVATAR, line)
        elif line == "x":
            return InputResult(InputCommand.DEMO_TOGGLE, line)
        elif line == "t":
            return InputResult(InputCommand.TOGGLE_DISPLAY, line)
        elif line == "d":
            return InputResult(InputCommand.TOGGLE_DEBUG, line)
        elif line == "w":
            return InputResult(InputCommand.TOGGLE_PREVIEW, line)
        elif line == "r":
            return InputResult(InputCommand.RESET, line)
        elif line == "h":
            return InputResult(InputCommand.HELP, line)
        elif line in ("q", "quit", "exit"):
            return InputResult(InputCommand.QUIT, line)
        else:
            return InputResult(InputCommand.NONE, line)

    def check_abort(self) -> bool:
        """Check if abort key (space) was pressed.

        Used during snapshot countdown/pause to check for abort.

        Returns:
            True if abort key was pressed.
        """
        result = self.check_input()
        if result.command == InputCommand.SNAPSHOT:
            return True
        return result.raw_input == " "

    def clear_buffer(self) -> None:
        """Clear any buffered input."""
        try:
            while select.select([sys.stdin], [], [], 0)[0]:
                if self._single_keypress and self._in_context:
                    sys.stdin.read(1)
                else:
                    sys.stdin.readline()
        except OSError, ValueError:
            pass

    def disable(self) -> None:
        """Disable keyboard input checking."""
        self._enabled = False

    def enable(self) -> None:
        """Enable keyboard input checking."""
        self._enabled = True


def print_help(
    orientation: str,
    processing_mode: str,
    black_and_white: bool,
    debug_mode: bool,
    zoom_level: float = 1.0,
    show_preview: bool = False,
    mirror: bool = False,
    render_algorithm_name: str = "squares",
    led_size_pct: int = 100,
) -> None:
    """Print help message with current settings.

    Args:
        orientation: Current orientation (landscape/portrait).
        processing_mode: Current processing mode (center/stretch/fit).
        black_and_white: Whether B&W mode is active.
        debug_mode: Whether debug mode is active.
        zoom_level: Current zoom level (0.25-1.0).
        show_preview: Whether preview window is enabled.
        mirror: Whether mirror mode is active.
        render_algorithm_name: Display name of current LED preview render algorithm.
        led_size_pct: Current LED size percentage (only applies to Circles).
    """
    print("")
    print("=" * 60)
    print("Commands (single keypress):")
    print("  Orientation: l=landscape  p=portrait")
    print("  Processing:  c=center  s=stretch  f=fit")
    print("  Effects:     b=B&W toggle  m=mirror toggle  z=zoom")
    print("  Preview:     w=on/off  o=algorithm  +/= size up  -/_ size down (Circles only)")
    print("  Actions:     SPACE=snapshot  v=avatar")
    print("  Demo:        x=auto  X=manual  ,/<  ./>  SPACE=pause/resume")
    print("  System:      t=toggle transmission  d=debug  r=reset  h=help  q=quit")
    print("")
    bw_str = "B&W" if black_and_white else "Color"
    debug_str = "ON" if debug_mode else "OFF"
    zoom_pct = int(zoom_level * 100)
    preview_str = "ON" if show_preview else "OFF"
    mirror_str = "ON" if mirror else "OFF"
    print(
        f"Current: {orientation.title()} + {processing_mode.title()}, {bw_str}, Mirror={mirror_str}, "
        f"Debug={debug_str}, Zoom={zoom_pct}%, Preview={preview_str}, "
        f"Algorithm={render_algorithm_name}, Size={led_size_pct}%"
    )
    print("=" * 60)
    print("")
