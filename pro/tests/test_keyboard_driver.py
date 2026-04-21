"""Tests for KeyboardDriver: injected stdin bytes → DriverState."""

from __future__ import annotations

from unittest.mock import patch

from ledportal_pro.avatar.drivers import DriverState
from ledportal_pro.avatar.drivers_impl.keyboard import KeyboardDriver

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def _make_driver(chars: list[str]) -> KeyboardDriver:
    """Build a KeyboardDriver whose stdin is pre-seeded with ``chars``."""
    with (
        patch("ledportal_pro.avatar.drivers_impl.keyboard.termios"),
        patch("ledportal_pro.avatar.drivers_impl.keyboard.tty"),
        patch.object(KeyboardDriver, "_print_controls"),
    ):
        driver = KeyboardDriver(fd=0)

    driver._read_pending = lambda: list(chars)  # type: ignore[method-assign]
    return driver


# ------------------------------------------------------------------ #
# Eye key mapping                                                     #
# ------------------------------------------------------------------ #


class TestEyeKeys:
    def test_1_maps_to_open(self):
        driver = _make_driver(["1"])
        assert driver.poll(0.0).eyes == "open"

    def test_2_maps_to_closed(self):
        driver = _make_driver(["2"])
        assert driver.poll(0.0).eyes == "closed"

    def test_3_maps_to_raised(self):
        driver = _make_driver(["3"])
        assert driver.poll(0.0).eyes == "raised"

    def test_4_maps_to_furrowed(self):
        driver = _make_driver(["4"])
        assert driver.poll(0.0).eyes == "furrowed"


# ------------------------------------------------------------------ #
# Mouth key mapping                                                   #
# ------------------------------------------------------------------ #


class TestMouthKeys:
    def test_5_maps_to_neutral(self):
        driver = _make_driver(["5"])
        assert driver.poll(0.0).mouth == "neutral"

    def test_6_maps_to_smile(self):
        driver = _make_driver(["6"])
        assert driver.poll(0.0).mouth == "smile"

    def test_7_maps_to_smile_open(self):
        driver = _make_driver(["7"])
        assert driver.poll(0.0).mouth == "smile_open"

    def test_8_maps_to_o(self):
        driver = _make_driver(["8"])
        assert driver.poll(0.0).mouth == "o"

    def test_9_maps_to_ee(self):
        driver = _make_driver(["9"])
        assert driver.poll(0.0).mouth == "ee"


# ------------------------------------------------------------------ #
# Angle key mapping                                                   #
# ------------------------------------------------------------------ #


class TestAngleKeys:
    def test_w_maps_to_up(self):
        driver = _make_driver(["w"])
        assert driver.poll(0.0).angle == "up"

    def test_s_maps_to_down(self):
        driver = _make_driver(["s"])
        assert driver.poll(0.0).angle == "down"

    def test_a_maps_to_left(self):
        driver = _make_driver(["a"])
        assert driver.poll(0.0).angle == "left"

    def test_d_maps_to_right(self):
        driver = _make_driver(["d"])
        assert driver.poll(0.0).angle == "right"

    def test_e_maps_to_front(self):
        driver = _make_driver(["e"])
        assert driver.poll(0.0).angle == "front"


# ------------------------------------------------------------------ #
# Stop keys                                                           #
# ------------------------------------------------------------------ #


class TestStopKeys:
    def test_q_triggers_stop(self):
        driver = _make_driver(["q"])
        driver.poll(0.0)
        assert driver.should_stop()

    def test_esc_triggers_stop(self):
        driver = _make_driver(["\x1b"])
        driver.poll(0.0)
        assert driver.should_stop()

    def test_no_stop_before_q(self):
        driver = _make_driver(["1"])
        driver.poll(0.0)
        assert not driver.should_stop()


# ------------------------------------------------------------------ #
# Multi-key polls (last key wins)                                     #
# ------------------------------------------------------------------ #


class TestMultiKeyPoll:
    def test_last_eye_key_wins(self):
        driver = _make_driver(["1", "2", "3"])
        state = driver.poll(0.0)
        assert state.eyes == "raised"  # "3" is last eye key

    def test_last_angle_key_wins(self):
        driver = _make_driver(["a", "d", "w"])
        state = driver.poll(0.0)
        assert state.angle == "up"  # "w" is last

    def test_eye_and_mouth_simultaneous(self):
        driver = _make_driver(["2", "6"])
        state = driver.poll(0.0)
        assert state.eyes == "closed"
        assert state.mouth == "smile"


# ------------------------------------------------------------------ #
# Empty poll                                                          #
# ------------------------------------------------------------------ #


class TestEmptyPoll:
    def test_no_keys_returns_all_none(self):
        driver = _make_driver([])
        state = driver.poll(0.0)
        assert state == DriverState()

    def test_unknown_key_ignored(self):
        driver = _make_driver(["z"])
        state = driver.poll(0.0)
        assert state == DriverState()
