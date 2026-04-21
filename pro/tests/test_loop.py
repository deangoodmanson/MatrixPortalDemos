"""Tests for AvatarLoop: frame timing, stop signal, and close-on-exit."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ledportal_pro.avatar.drivers import DriverState
from ledportal_pro.avatar.loop import AvatarLoop
from ledportal_pro.avatar.resolver import VariantResolver
from ledportal_pro.avatar.schema import (
    SCHEMA_VERSION,
    AvatarAsset,
    BaseLayerSpec,
    PaletteColor,
    SpriteSheetSpec,
)

# ------------------------------------------------------------------ #
# Synthetic driver helpers                                            #
# ------------------------------------------------------------------ #


class _ScriptedDriver:
    """Emits a fixed sequence of DriverStates then stops."""

    def __init__(self, states: list[DriverState]) -> None:
        self._states = list(states)
        self._index = 0
        self.closed = False
        self.polls: list[DriverState] = []

    def poll(self, dt: float) -> DriverState:  # noqa: ARG002
        if self._index < len(self._states):
            s = self._states[self._index]
            self._index += 1
        else:
            s = DriverState()
        self.polls.append(s)
        return s

    def should_stop(self) -> bool:
        return self._index >= len(self._states)

    def close(self) -> None:
        self.closed = True


def _minimal_asset() -> AvatarAsset:
    return AvatarAsset(
        version=SCHEMA_VERSION,
        source_session="test",
        palette=[
            PaletteColor(0, 0, 0),
            PaletteColor(255, 255, 255),
            PaletteColor(128, 0, 0),
            PaletteColor(0, 128, 0),
        ],
        base=BaseLayerSpec(file="base.png"),
        features={
            "eyes": SpriteSheetSpec(
                sheet="eyes_sheet.png",
                sprite_size=(8, 3),
                anchor=(10, 8),
                variants=["front_neutral"],
            ),
            "mouth": SpriteSheetSpec(
                sheet="mouth_sheet.png",
                sprite_size=(10, 4),
                anchor=(12, 20),
                variants=["front_neutral"],
            ),
        },
    )


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #


class TestAvatarLoopStopSignal:
    def test_loop_exits_when_driver_should_stop(self):
        driver = _ScriptedDriver([DriverState(angle="front")])
        player = MagicMock()
        resolver = VariantResolver(_minimal_asset())

        loop = AvatarLoop(player, driver, resolver, target_fps=60.0)
        loop.run()

        assert driver.closed
        assert player.send_frame.call_count == 1

    def test_loop_runs_all_scripted_states(self):
        states = [
            DriverState(angle="front"),
            DriverState(eyes="closed"),
            DriverState(mouth="smile"),
        ]
        driver = _ScriptedDriver(states)
        player = MagicMock()
        resolver = VariantResolver(_minimal_asset())

        loop = AvatarLoop(player, driver, resolver, target_fps=1000.0)
        loop.run()

        assert player.send_frame.call_count == len(states)


class TestAvatarLoopClose:
    def test_close_called_on_keyboard_interrupt(self):
        class _InterruptDriver:
            def __init__(self) -> None:
                self.closed = False
                self._calls = 0

            def poll(self, dt: float) -> DriverState:  # noqa: ARG002
                self._calls += 1
                if self._calls >= 2:
                    raise KeyboardInterrupt
                return DriverState()

            def should_stop(self) -> bool:
                return False

            def close(self) -> None:
                self.closed = True

        driver = _InterruptDriver()
        player = MagicMock()
        resolver = VariantResolver(_minimal_asset())

        loop = AvatarLoop(player, driver, resolver, target_fps=1000.0)
        loop.run()  # should not propagate KeyboardInterrupt

        assert driver.closed


class TestAvatarLoopTiming:
    def test_sleep_called_when_render_is_fast(self):
        driver = _ScriptedDriver([DriverState()])
        player = MagicMock()
        resolver = VariantResolver(_minimal_asset())

        loop = AvatarLoop(player, driver, resolver, target_fps=15.0)

        with (
            patch("ledportal_pro.avatar.loop.time.sleep") as mock_sleep,
            patch(
                "ledportal_pro.avatar.loop.time.monotonic",
                side_effect=[
                    0.0,  # prev = now = start of loop
                    0.0,  # now (after poll)
                    0.001,  # elapsed after send_frame (1 ms render)
                ],
            ),
        ):
            loop.run()

        # remaining = 1/15 - 0.001 > 0 → sleep should have been called
        assert mock_sleep.call_count >= 1
        slept = mock_sleep.call_args[0][0]
        assert slept > 0

    def test_no_sleep_when_render_exceeds_budget(self):
        driver = _ScriptedDriver([DriverState()])
        player = MagicMock()
        resolver = VariantResolver(_minimal_asset())

        loop = AvatarLoop(player, driver, resolver, target_fps=15.0)

        with (
            patch("ledportal_pro.avatar.loop.time.sleep") as mock_sleep,
            patch(
                "ledportal_pro.avatar.loop.time.monotonic",
                side_effect=[
                    0.0,  # prev
                    0.0,  # now (loop start)
                    0.200,  # elapsed after render (200 ms — over budget at 15 fps)
                ],
            ),
        ):
            loop.run()

        assert mock_sleep.call_count == 0


class TestAvatarLoopResolverIntegration:
    def test_set_state_called_for_changed_features(self):
        driver = _ScriptedDriver([DriverState(angle="front", eyes="open", mouth="neutral")])
        player = MagicMock()
        resolver = VariantResolver(_minimal_asset())

        loop = AvatarLoop(player, driver, resolver, target_fps=1000.0)
        loop.run()

        # set_state should have been called for eyes and mouth
        feature_calls = {c.args[0] for c in player.set_state.call_args_list}
        assert "eyes" in feature_calls
        assert "mouth" in feature_calls
