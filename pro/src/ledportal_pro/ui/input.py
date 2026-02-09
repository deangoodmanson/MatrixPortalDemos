"""Keyboard input handling with single-keypress support."""

import select
import sys
import termios
import tty
from dataclasses import dataclass
from enum import Enum, auto
from types import TracebackType


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
    # Actions
    SNAPSHOT = auto()
    AVATAR = auto()  # Avatar capture mode
    TOGGLE_DEBUG = auto()
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
        self._old_settings: list[int] | None = None
        self._in_context = False

    def __enter__(self) -> KeyboardHandler:
        """Enter context manager, set terminal to cbreak mode."""
        self._in_context = True
        if self._single_keypress:
            try:
                self._old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except (termios.error, OSError):
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
            except (termios.error, OSError):
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
                    # Single character read
                    char = sys.stdin.read(1).lower()
                    return self._parse_single_key(char)
                else:
                    # Line-based input
                    line = sys.stdin.readline().strip().lower()
                    return self._parse_line(line)
        except (OSError, ValueError):
            pass

        return InputResult(InputCommand.NONE)

    def _parse_single_key(self, char: str) -> InputResult:
        """Parse single keypress into command.

        Args:
            char: Single character input.

        Returns:
            InputResult with the parsed command.
        """
        key_map = {
            # Display orientation
            "l": InputCommand.ORIENTATION_LANDSCAPE,
            "p": InputCommand.ORIENTATION_PORTRAIT,
            # Processing modes
            "c": InputCommand.PROCESSING_CENTER,
            "s": InputCommand.PROCESSING_STRETCH,
            "r": InputCommand.PROCESSING_FIT,
            # Effects
            "b": InputCommand.TOGGLE_BW,
            # Actions
            " ": InputCommand.SNAPSHOT,
            "v": InputCommand.AVATAR,
            "d": InputCommand.TOGGLE_DEBUG,
            "h": InputCommand.HELP,
            "q": InputCommand.QUIT,
        }

        command = key_map.get(char, InputCommand.NONE)
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
        elif line == "r":
            return InputResult(InputCommand.PROCESSING_FIT, line)
        elif line == "b":
            return InputResult(InputCommand.TOGGLE_BW, line)
        elif line == "v":
            return InputResult(InputCommand.AVATAR, line)
        elif line == "d":
            return InputResult(InputCommand.TOGGLE_DEBUG, line)
        elif line == "h":
            return InputResult(InputCommand.HELP, line)
        elif line in ("q", "quit", "exit"):
            return InputResult(InputCommand.QUIT, line)
        else:
            return InputResult(InputCommand.NONE, line)

    def check_abort(self) -> bool:
        """Check if abort key (space or r) was pressed.

        Used during snapshot countdown/pause to check for abort.

        Returns:
            True if abort key was pressed.
        """
        result = self.check_input()
        if result.command in (InputCommand.SNAPSHOT, InputCommand.PROCESSING_FIT):
            return True
        return result.raw_input in (" ", "r")

    def clear_buffer(self) -> None:
        """Clear any buffered input."""
        try:
            while select.select([sys.stdin], [], [], 0)[0]:
                if self._single_keypress and self._in_context:
                    sys.stdin.read(1)
                else:
                    sys.stdin.readline()
        except (OSError, ValueError):
            pass

    def disable(self) -> None:
        """Disable keyboard input checking."""
        self._enabled = False

    def enable(self) -> None:
        """Enable keyboard input checking."""
        self._enabled = True


def print_help(
    orientation: str, processing_mode: str, black_and_white: bool, debug_mode: bool
) -> None:
    """Print help message with current settings.

    Args:
        orientation: Current orientation (landscape/portrait).
        processing_mode: Current processing mode (center/stretch/fit).
        black_and_white: Whether B&W mode is active.
        debug_mode: Whether debug mode is active.
    """
    print("")
    print("=" * 60)
    print("Commands (single keypress):")
    print("  Orientation: l=landscape  p=portrait")
    print("  Processing:  c=center  s=stretch  r=fit")
    print("  Effects:     b=toggle B&W/Color")
    print("  Actions:     SPACE=snapshot  v=avatar  d=debug  h=help  q=quit")
    print("")
    bw_str = "B&W" if black_and_white else "Color"
    debug_str = "ON" if debug_mode else "OFF"
    print(f"Current: {orientation.title()} + {processing_mode.title()}, {bw_str}, Debug={debug_str}")
    print("=" * 60)
    print("")
