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
    # Display modes
    MODE_LANDSCAPE = auto()
    MODE_PORTRAIT = auto()
    MODE_SQUISH = auto()
    MODE_LETTERBOX = auto()
    # Effects
    BLACK_WHITE = auto()
    COLOR = auto()
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
            # Display modes
            "c": InputCommand.MODE_LANDSCAPE,
            "s": InputCommand.MODE_SQUISH,
            "l": InputCommand.MODE_LETTERBOX,
            "p": InputCommand.MODE_PORTRAIT,
            # Effects
            "b": InputCommand.BLACK_WHITE,
            "n": InputCommand.COLOR,
            # Actions
            " ": InputCommand.SNAPSHOT,
            "v": InputCommand.AVATAR,
            "d": InputCommand.TOGGLE_DEBUG,
            "r": InputCommand.RESET,
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
        elif line == "b":
            return InputResult(InputCommand.BLACK_WHITE, line)
        elif line == "n":
            return InputResult(InputCommand.COLOR, line)
        elif line == "c":
            return InputResult(InputCommand.MODE_LANDSCAPE, line)
        elif line == "s":
            return InputResult(InputCommand.MODE_SQUISH, line)
        elif line == "l":
            return InputResult(InputCommand.MODE_LETTERBOX, line)
        elif line == "p":
            return InputResult(InputCommand.MODE_PORTRAIT, line)
        elif line == "v":
            return InputResult(InputCommand.AVATAR, line)
        elif line == "d":
            return InputResult(InputCommand.TOGGLE_DEBUG, line)
        elif line == "r":
            return InputResult(InputCommand.RESET, line)
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
        if result.command in (InputCommand.SNAPSHOT, InputCommand.RESET):
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


def print_help(display_mode: str, black_and_white: bool, debug_mode: bool) -> None:
    """Print help message with current settings.

    Args:
        display_mode: Current display mode.
        black_and_white: Whether B&W mode is active.
        debug_mode: Whether debug mode is active.
    """
    print("")
    print("=" * 50)
    print("Commands (single keypress):")
    print("  Display: c=crop  s=squish  l=letterbox  p=portrait")
    print("  Effects: b=B&W  n=normal(color)")
    print("  Actions: SPACE=snapshot  v=avatar  d=debug  r=reset  h=help  q=quit")
    print("")
    bw_str = "B&W" if black_and_white else "Color"
    debug_str = "ON" if debug_mode else "OFF"
    print(f"Current: Mode={display_mode}, {bw_str}, Debug={debug_str}")
    print("=" * 50)
    print("")
