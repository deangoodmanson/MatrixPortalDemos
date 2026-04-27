"""Tests for DemoMode — sequence structure, timer logic, and navigation."""

import time

import pytest

from ledportal_pro.ui.demo import DemoMode, DemoState, _build_sequence
from ledportal_pro.ui.input import InputCommand


# ---------------------------------------------------------------------------
# Sequence structure
# ---------------------------------------------------------------------------


class TestSequenceStructure:
    """The built sequence contains the expected commands in the right order."""

    def test_sequence_nonempty(self):
        seq = _build_sequence(3.0)
        assert len(seq) > 0

    def test_sequence_starts_with_landscape(self):
        seq = _build_sequence(3.0)
        assert seq[0].command == InputCommand.ORIENTATION_LANDSCAPE

    def test_sequence_contains_portrait(self):
        commands = [s.command for s in _build_sequence(3.0)]
        assert InputCommand.ORIENTATION_PORTRAIT in commands

    def test_portrait_comes_after_landscape(self):
        commands = [s.command for s in _build_sequence(3.0)]
        landscape_idx = commands.index(InputCommand.ORIENTATION_LANDSCAPE)
        portrait_idx = commands.index(InputCommand.ORIENTATION_PORTRAIT)
        assert landscape_idx < portrait_idx

    def test_sequence_ends_after_portrait(self):
        """Portrait is not the last step — portrait effects follow it."""
        commands = [s.command for s in _build_sequence(3.0)]
        portrait_idx = commands.index(InputCommand.ORIENTATION_PORTRAIT)
        assert portrait_idx < len(commands) - 1

    def test_all_steps_have_nonnegative_duration(self):
        for step in _build_sequence(3.0):
            assert step.duration >= 0.0

    def test_instant_steps_have_zero_duration(self):
        """Restore-only steps (empty label) are instant."""
        instant = [s for s in _build_sequence(3.0) if s.duration == 0.0]
        assert len(instant) > 0
        for step in instant:
            assert step.label == ""

    def test_sequence_restores_bw(self):
        """B&W is toggled on then off within the sequence."""
        commands = [s.command for s in _build_sequence(3.0)]
        bw_toggles = [i for i, c in enumerate(commands) if c == InputCommand.TOGGLE_BW]
        assert len(bw_toggles) >= 2

    def test_sequence_restores_mirror(self):
        commands = [s.command for s in _build_sequence(3.0)]
        mirror_toggles = [i for i, c in enumerate(commands) if c == InputCommand.TOGGLE_MIRROR]
        assert len(mirror_toggles) >= 2


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


class TestStateTransitions:
    def test_initial_state_is_off(self):
        demo = DemoMode()
        assert demo.state == DemoState.OFF
        assert not demo.is_active

    def test_start_auto_sets_auto_state(self):
        demo = DemoMode()
        demo.start_auto()
        assert demo.state == DemoState.AUTO
        assert demo.is_active

    def test_start_manual_sets_manual_state(self):
        demo = DemoMode()
        demo.start_manual()
        assert demo.state == DemoState.MANUAL

    def test_stop_returns_to_off(self):
        demo = DemoMode()
        demo.start_auto()
        demo.stop()
        assert demo.state == DemoState.OFF
        assert not demo.is_active

    def test_pause_from_auto(self):
        demo = DemoMode()
        demo.start_auto()
        demo.pause()
        assert demo.state == DemoState.PAUSED

    def test_resume_from_paused(self):
        demo = DemoMode()
        demo.start_auto()
        demo.pause()
        demo.resume()
        assert demo.state == DemoState.AUTO

    def test_pause_ignored_when_not_auto(self):
        demo = DemoMode()
        demo.start_manual()
        demo.pause()
        assert demo.state == DemoState.MANUAL

    def test_resume_ignored_when_not_paused(self):
        demo = DemoMode()
        demo.start_auto()
        demo.resume()
        assert demo.state == DemoState.AUTO

    def test_toggle_pause_auto_to_paused(self):
        demo = DemoMode()
        demo.start_auto()
        new_state = demo.toggle_pause()
        assert new_state == DemoState.PAUSED

    def test_toggle_pause_paused_to_auto(self):
        demo = DemoMode()
        demo.start_auto()
        demo.pause()
        new_state = demo.toggle_pause()
        assert new_state == DemoState.AUTO


# ---------------------------------------------------------------------------
# get_next_command — timer logic
# ---------------------------------------------------------------------------


class TestGetNextCommand:
    def test_returns_none_when_off(self):
        demo = DemoMode()
        assert demo.get_next_command(time.time()) is None

    def test_returns_none_when_paused(self):
        demo = DemoMode()
        demo.start_auto()
        demo.pause()
        # Even after a long wait, paused never fires
        assert demo.get_next_command(time.time() + 9999) is None

    def test_returns_none_when_manual(self):
        demo = DemoMode()
        demo.start_manual()
        assert demo.get_next_command(time.time() + 9999) is None

    def test_fires_immediately_on_start(self):
        """_step_start_time == 0.0 sentinel means fire without waiting."""
        demo = DemoMode(step_duration=3.0)
        demo.start_auto()
        result = demo.get_next_command(time.time())
        assert result is not None
        assert result.command == InputCommand.ORIENTATION_LANDSCAPE

    def test_does_not_fire_before_duration(self):
        demo = DemoMode(step_duration=3.0)
        demo.start_auto()
        demo.get_next_command(time.time())  # consume first step (fires immediately)
        t = time.time()
        # Almost immediately after — well under 3 s
        result = demo.get_next_command(t + 0.1)
        assert result is None

    def test_fires_after_duration(self):
        demo = DemoMode(step_duration=3.0)
        demo.start_auto()
        demo.get_next_command(time.time())  # consume first step
        t = time.time()
        result = demo.get_next_command(t + 3.1)
        assert result is not None

    def test_instant_steps_fire_on_next_call(self):
        """Steps with duration=0.0 fire even with only a tiny time delta."""
        seq = _build_sequence(3.0)
        instant_idx = next(i for i, s in enumerate(seq) if s.duration == 0.0)

        demo = DemoMode(step_duration=3.0)
        demo.start_auto()

        t = 1000.0
        # Consume steps up to (but not including) the instant step
        for i in range(instant_idx):
            while demo.get_next_command(t) is None:
                t += 3.1

        # Now the current step is the instant one — it should fire immediately
        result = demo.get_next_command(t + 0.001)
        assert result is not None
        assert result.command == seq[instant_idx].command

    def test_advances_index_after_firing(self):
        demo = DemoMode(step_duration=1.0)
        demo.start_auto()
        t = time.time()
        demo.get_next_command(t)  # step 0 fires immediately
        demo.get_next_command(t + 1.1)  # step 1 fires
        pos = demo.step_position
        assert pos.startswith("3/")  # now on step 3 (1-indexed)

    def test_wraps_around_after_last_step(self):
        demo = DemoMode(step_duration=0.001)
        demo.start_auto()
        total = len(demo._sequence)
        t = 0.0
        fired = 0
        while fired < total + 2:
            result = demo.get_next_command(t)
            if result is not None:
                fired += 1
            t += 0.01
        # Successfully wrapped — no IndexError raised, still active
        assert demo.is_active


# ---------------------------------------------------------------------------
# next_step / prev_step — navigation and timer reset
# ---------------------------------------------------------------------------


class TestNavigation:
    def test_next_step_returns_current_command(self):
        demo = DemoMode()
        demo.start_auto()
        seq = demo._sequence
        first_cmd = seq[0].command
        result = demo.next_step()
        assert result.command == first_cmd

    def test_next_step_advances_index(self):
        demo = DemoMode()
        demo.start_auto()
        demo.next_step()
        assert demo.step_position.startswith("2/")

    def test_next_step_sets_real_time_not_zero(self):
        """After next_step(), auto-advance should wait a full duration — not fire immediately.

        This is the regression caught by PR #15: _step_start_time was mistakenly
        set to 0.0, causing the following step to fire on the very next frame.
        """
        demo = DemoMode(step_duration=3.0)
        demo.start_auto()
        demo.next_step()
        # With _step_start_time = time.time(), a call 0.1s later should NOT fire
        result = demo.get_next_command(time.time() + 0.1)
        assert result is None, (
            "next_step() must set _step_start_time to time.time(), not 0.0; "
            "otherwise the following step fires immediately (double-fire bug)"
        )

    def test_prev_step_sets_real_time_not_zero(self):
        """Same guard for prev_step()."""
        demo = DemoMode(step_duration=3.0)
        demo.start_auto()
        demo.next_step()  # advance once so prev_step has somewhere to go
        demo.prev_step()
        result = demo.get_next_command(time.time() + 0.1)
        assert result is None, (
            "prev_step() must set _step_start_time to time.time(), not 0.0"
        )

    def test_prev_step_wraps_around(self):
        demo = DemoMode()
        demo.start_auto()
        total = len(demo._sequence)
        # At step 0, prev should wrap to the last step
        result = demo.prev_step()
        seq = demo._sequence
        assert result.command == seq[total - 1].command

    def test_next_step_wraps_around(self):
        demo = DemoMode(step_duration=0.001)
        demo.start_auto()
        total = len(demo._sequence)
        for _ in range(total):
            demo.next_step()
        # After total advances, back to step 0
        result = demo.next_step()
        assert result.command == demo._sequence[0].command

    def test_step_position_string_format(self):
        demo = DemoMode()
        demo.start_auto()
        pos = demo.step_position
        parts = pos.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()


# ---------------------------------------------------------------------------
# Full sequence walk — portrait must be visited
# ---------------------------------------------------------------------------


class TestFullSequenceWalk:
    def test_auto_advance_visits_portrait(self):
        """Simulate auto-advance through the full sequence; portrait must fire."""
        demo = DemoMode(step_duration=0.001)
        demo.start_auto()
        fired_commands = []
        t = 0.0
        # Drive through two full loops to confirm wrap-around works too
        target = len(demo._sequence) * 2
        while len(fired_commands) < target:
            result = demo.get_next_command(t)
            if result is not None:
                fired_commands.append(result.command)
            t += 0.01
        assert InputCommand.ORIENTATION_PORTRAIT in fired_commands

    def test_auto_advance_visits_landscape_before_portrait(self):
        demo = DemoMode(step_duration=0.001)
        demo.start_auto()
        first_landscape = None
        first_portrait = None
        fired = []
        t = 0.0
        while len(fired) < len(demo._sequence):
            result = demo.get_next_command(t)
            if result is not None:
                fired.append(result.command)
                if first_landscape is None and result.command == InputCommand.ORIENTATION_LANDSCAPE:
                    first_landscape = len(fired)
                if first_portrait is None and result.command == InputCommand.ORIENTATION_PORTRAIT:
                    first_portrait = len(fired)
            t += 0.01
        assert first_landscape is not None
        assert first_portrait is not None
        assert first_landscape < first_portrait
