"""Tests for keyboard input parsing."""

import pytest

from ledportal_pro.ui.input import InputCommand, InputResult, KeyboardHandler

# ---------------------------------------------------------------------------
# Single-key mapping — tests _parse_single_key via a freshly constructed handler
# (no terminal manipulation needed; we call the method directly)
# ---------------------------------------------------------------------------


class TestSingleKeyParsing:
    """Every bound key maps to the correct InputCommand."""

    EXPECTED_MAP = {
        "l": InputCommand.ORIENTATION_LANDSCAPE,
        "p": InputCommand.ORIENTATION_PORTRAIT,
        "c": InputCommand.PROCESSING_CENTER,
        "s": InputCommand.PROCESSING_STRETCH,
        "f": InputCommand.PROCESSING_FIT,
        "b": InputCommand.TOGGLE_BW,
        "z": InputCommand.ZOOM_TOGGLE,
        " ": InputCommand.SNAPSHOT,
        "v": InputCommand.AVATAR,
        "t": InputCommand.TOGGLE_DISPLAY,
        "d": InputCommand.TOGGLE_DEBUG,
        "r": InputCommand.RESET,
        "h": InputCommand.HELP,
        "q": InputCommand.QUIT,
    }

    @pytest.mark.parametrize("key,expected_cmd", EXPECTED_MAP.items())
    def test_key_produces_correct_command(self, key, expected_cmd):
        handler = KeyboardHandler(single_keypress=False)
        result = handler._parse_single_key(key)
        assert result.command == expected_cmd
        assert result.raw_input == key

    def test_unbound_key_returns_none(self):
        handler = KeyboardHandler(single_keypress=False)
        result = handler._parse_single_key("x")
        assert result.command == InputCommand.NONE
        assert result.raw_input == "x"

    def test_uppercase_not_mapped(self):
        """Key map uses lowercase; uppercase should be NONE (caller lowercases)."""
        handler = KeyboardHandler(single_keypress=False)
        result = handler._parse_single_key("Q")
        assert result.command == InputCommand.NONE


# ---------------------------------------------------------------------------
# Line-based fallback parsing (_parse_line)
# ---------------------------------------------------------------------------


class TestLineParsing:
    """Fallback line-mode parsing maps the same commands."""

    LINE_MAP = {
        "l": InputCommand.ORIENTATION_LANDSCAPE,
        "p": InputCommand.ORIENTATION_PORTRAIT,
        "c": InputCommand.PROCESSING_CENTER,
        "s": InputCommand.PROCESSING_STRETCH,
        "f": InputCommand.PROCESSING_FIT,
        "b": InputCommand.TOGGLE_BW,
        "z": InputCommand.ZOOM_TOGGLE,
        "v": InputCommand.AVATAR,
        "t": InputCommand.TOGGLE_DISPLAY,
        "d": InputCommand.TOGGLE_DEBUG,
        "r": InputCommand.RESET,
        "h": InputCommand.HELP,
    }

    @pytest.mark.parametrize("line,expected_cmd", LINE_MAP.items())
    def test_line_produces_correct_command(self, line, expected_cmd):
        handler = KeyboardHandler(single_keypress=False)
        result = handler._parse_line(line)
        assert result.command == expected_cmd

    def test_empty_line_is_snapshot(self):
        """Enter with no text = snapshot (same as space in single-key mode)."""
        handler = KeyboardHandler(single_keypress=False)
        result = handler._parse_line("")
        assert result.command == InputCommand.SNAPSHOT

    @pytest.mark.parametrize("quit_word", ["q", "quit", "exit"])
    def test_quit_aliases(self, quit_word):
        handler = KeyboardHandler(single_keypress=False)
        result = handler._parse_line(quit_word)
        assert result.command == InputCommand.QUIT

    def test_unknown_line_is_none(self):
        handler = KeyboardHandler(single_keypress=False)
        result = handler._parse_line("garbage")
        assert result.command == InputCommand.NONE


# ---------------------------------------------------------------------------
# InputCommand and InputResult data contracts
# ---------------------------------------------------------------------------


class TestInputCommand:
    """InputCommand enum covers all expected commands."""

    REQUIRED_COMMANDS = {
        "NONE",
        "ORIENTATION_LANDSCAPE",
        "ORIENTATION_PORTRAIT",
        "PROCESSING_CENTER",
        "PROCESSING_STRETCH",
        "PROCESSING_FIT",
        "TOGGLE_BW",
        "TOGGLE_MIRROR",
        "ZOOM_TOGGLE",
        "CYCLE_PREVIEW_MODE",
        "SNAPSHOT",
        "AVATAR",
        "TOGGLE_DISPLAY",
        "TOGGLE_DEBUG",
        "TOGGLE_PREVIEW",
        "RESET",
        "HELP",
        "QUIT",
        "ABORT",
    }

    def test_all_required_commands_exist(self):
        names = {cmd.name for cmd in InputCommand}
        assert names == self.REQUIRED_COMMANDS


class TestInputResult:
    """InputResult dataclass behaves correctly."""

    def test_default_raw_input_is_none(self):
        result = InputResult(command=InputCommand.NONE)
        assert result.raw_input is None

    def test_raw_input_stored(self):
        result = InputResult(command=InputCommand.QUIT, raw_input="q")
        assert result.raw_input == "q"
