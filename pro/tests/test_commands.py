"""Tests for keyboard-command handlers (commands.py).

These are the first direct tests of the main loop's command logic, made possible
by Phase 2's SessionState + handler extraction. Pure-state handlers are exercised
with a minimal LoopContext; handlers that need hardware collaborators
(snapshot/avatar/transport reconnect) are out of scope here.
"""

import argparse

import pytest

from ledportal_pro.commands import COMMAND_HANDLERS
from ledportal_pro.config import AppConfig
from ledportal_pro.session import HandlerResult, LoopContext, SessionState
from ledportal_pro.ui import DemoMode, InputCommand, PreviewAlgorithm
from ledportal_pro.ui.overlay import LED_SIZE_DEFAULT, LED_SIZE_STEPS


def make_state(**overrides: object) -> SessionState:
    """A SessionState with sensible defaults, overridable per test."""
    state = SessionState(orientation="landscape", processing_mode="center")
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def make_ctx() -> LoopContext:
    """A LoopContext sufficient for pure-state handlers.

    camera/snapshot_manager/keyboard are ``None`` because the handlers tested here
    never touch them; only config and demo are used.
    """
    return LoopContext(
        config=AppConfig(),
        args=argparse.Namespace(port=None),
        camera=None,  # type: ignore[arg-type]
        snapshot_manager=None,  # type: ignore[arg-type]
        keyboard=None,  # type: ignore[arg-type]
        demo=DemoMode(),
    )


def run(cmd: InputCommand, state: SessionState, ctx: LoopContext | None = None) -> HandlerResult:
    return COMMAND_HANDLERS[cmd](state, ctx or make_ctx())


class TestEffects:
    def test_toggle_bw_flips_and_falls_through_to_render(self):
        state = make_state(black_and_white=False)
        result = run(InputCommand.TOGGLE_BW, state)
        assert state.black_and_white is True
        assert result is HandlerResult.CONTINUE
        run(InputCommand.TOGGLE_BW, state)
        assert state.black_and_white is False

    def test_toggle_mirror(self):
        state = make_state(mirror_mode=False)
        run(InputCommand.TOGGLE_MIRROR, state)
        assert state.mirror_mode is True

    def test_cycle_render_algorithm_wraps(self):
        state = make_state(render_algorithm=PreviewAlgorithm.SQUARES)
        seen = {state.render_algorithm}
        for _ in range(len(PreviewAlgorithm)):
            run(InputCommand.CYCLE_RENDER_ALGORITHM, state)
            seen.add(state.render_algorithm)
        # Cycled through every algorithm and returned to the start
        assert seen == set(PreviewAlgorithm)
        assert state.render_algorithm == PreviewAlgorithm.SQUARES


class TestZoom:
    def test_zoom_cycles_full_circle(self):
        state = make_state(zoom_level=1.0)
        for expected in (0.75, 0.5, 0.25, 1.0):
            run(InputCommand.ZOOM_TOGGLE, state)
            assert state.zoom_level == expected


class TestLedSize:
    def test_increase_only_in_circles_mode(self):
        state = make_state(render_algorithm=PreviewAlgorithm.SQUARES, led_size_pct=LED_SIZE_DEFAULT)
        run(InputCommand.LED_SIZE_INCREASE, state)
        assert state.led_size_pct == LED_SIZE_DEFAULT  # unchanged outside CIRCLES

    def test_increase_clamps_at_top(self):
        state = make_state(
            render_algorithm=PreviewAlgorithm.CIRCLES, led_size_pct=LED_SIZE_STEPS[-1]
        )
        run(InputCommand.LED_SIZE_INCREASE, state)
        assert state.led_size_pct == LED_SIZE_STEPS[-1]

    def test_decrease_clamps_at_bottom(self):
        state = make_state(
            render_algorithm=PreviewAlgorithm.CIRCLES, led_size_pct=LED_SIZE_STEPS[0]
        )
        run(InputCommand.LED_SIZE_DECREASE, state)
        assert state.led_size_pct == LED_SIZE_STEPS[0]

    def test_increase_steps_up(self):
        state = make_state(
            render_algorithm=PreviewAlgorithm.CIRCLES, led_size_pct=LED_SIZE_STEPS[0]
        )
        run(InputCommand.LED_SIZE_INCREASE, state)
        assert state.led_size_pct == LED_SIZE_STEPS[1]


class TestOrientationAndProcessing:
    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            (InputCommand.ORIENTATION_LANDSCAPE, "landscape"),
            (InputCommand.ORIENTATION_PORTRAIT, "portrait"),
        ],
    )
    def test_orientation(self, cmd, expected):
        state = make_state(orientation="landscape")
        run(cmd, state)
        assert state.orientation == expected

    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            (InputCommand.PROCESSING_CENTER, "center"),
            (InputCommand.PROCESSING_STRETCH, "stretch"),
            (InputCommand.PROCESSING_FIT, "fit"),
        ],
    )
    def test_processing(self, cmd, expected):
        state = make_state(processing_mode="center")
        run(cmd, state)
        assert state.processing_mode == expected


class TestSystem:
    def test_toggle_debug(self):
        state = make_state(debug_mode=False)
        result = run(InputCommand.TOGGLE_DEBUG, state)
        assert state.debug_mode is True
        assert result is HandlerResult.CONTINUE

    def test_quit_breaks(self):
        result = run(InputCommand.QUIT, make_state())
        assert result is HandlerResult.BREAK

    def test_reset_restores_all_view_defaults(self):
        state = make_state(
            orientation="portrait",
            processing_mode="fit",
            black_and_white=True,
            mirror_mode=True,
            zoom_level=0.25,
            render_algorithm=PreviewAlgorithm.SQUARES,
            led_size_pct=LED_SIZE_STEPS[0],
            debug_mode=True,
            display_enabled=False,
        )
        run(InputCommand.RESET, state)
        assert state.orientation == "landscape"
        assert state.processing_mode == "center"
        assert state.black_and_white is False
        assert state.mirror_mode is False
        assert state.zoom_level == 1.0
        assert state.render_algorithm == PreviewAlgorithm.GAUSSIAN_DIFFUSED
        assert state.led_size_pct == LED_SIZE_DEFAULT
        assert state.debug_mode is False
        assert state.display_enabled is True


class TestResetView:
    def test_reset_view_does_not_touch_debug_or_display(self):
        """reset_view() is the shared view-only reset; RESET layers debug/display on top."""
        state = make_state(debug_mode=True, display_enabled=False, orientation="portrait")
        state.reset_view()
        assert state.orientation == "landscape"
        # view-only reset leaves these alone
        assert state.debug_mode is True
        assert state.display_enabled is False


class TestDispatchTable:
    def test_every_handler_has_uniform_signature(self):
        """Each handler returns a HandlerResult for a no-collaborator command set."""
        for cmd in (
            InputCommand.TOGGLE_BW,
            InputCommand.TOGGLE_MIRROR,
            InputCommand.TOGGLE_DEBUG,
            InputCommand.RESET,
            InputCommand.ZOOM_TOGGLE,
            InputCommand.ORIENTATION_PORTRAIT,
        ):
            assert isinstance(run(cmd, make_state()), HandlerResult)
