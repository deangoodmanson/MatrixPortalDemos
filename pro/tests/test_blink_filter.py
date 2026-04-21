"""Tests for BlinkFilter driver middleware."""

from __future__ import annotations

from ledportal_pro.avatar.drivers import DriverState
from ledportal_pro.avatar.loop import BlinkFilter

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


class _SteadyDriver:
    """Always emits the same DriverState with eyes=open."""

    def __init__(self, eyes: str = "open") -> None:
        self._state = DriverState(angle="front", eyes=eyes, mouth="neutral")
        self.closed = False

    def poll(self, dt: float) -> DriverState:  # noqa: ARG002
        return self._state

    def should_stop(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #


class TestBlinkFilterBehavior:
    def test_pass_through_before_first_blink(self):
        """Before the blink interval elapses, the inner state is passed through."""
        inner = _SteadyDriver(eyes="open")
        blink = BlinkFilter(inner, interval_range=(10.0, 10.0), blink_duration=0.12)

        state = blink.poll(0.01)  # tiny dt — nowhere near 10 s interval
        assert state.eyes == "open"

    def test_blink_fires_after_interval(self):
        """After accumulating enough dt, the blink fires."""
        inner = _SteadyDriver(eyes="open")
        blink = BlinkFilter(inner, interval_range=(1.0, 1.0), blink_duration=0.12)

        # Accumulate 1.0 s of dt in small increments
        state = None
        for _ in range(100):
            state = blink.poll(0.011)  # 100 × 0.011 = 1.1 s > interval of 1.0 s
            if state.eyes == "closed":
                break

        assert state is not None and state.eyes == "closed"

    def test_blink_lasts_for_duration(self):
        """The closed override persists for blink_duration."""
        inner = _SteadyDriver(eyes="open")
        blink = BlinkFilter(inner, interval_range=(0.0, 0.0), blink_duration=0.5)

        # First poll after interval=0 → blink fires
        blink.poll(0.0)
        s = blink.poll(0.1)  # 0.1 s into blink, still within 0.5 s duration
        assert s.eyes == "closed"

    def test_blink_ends_after_duration(self):
        """After blink_duration has elapsed, eyes return to open."""
        inner = _SteadyDriver(eyes="open")
        blink = BlinkFilter(inner, interval_range=(0.0, 0.0), blink_duration=0.1)

        blink.poll(0.0)  # fires blink
        blink.poll(0.05)  # mid-blink → closed
        s = blink.poll(0.1)  # 0.05+0.1=0.15 > 0.1 duration → blink over
        assert s.eyes == "open"

    def test_no_blink_when_inner_already_closed(self):
        """Blink timer should only tick when inner eyes are 'open'."""
        inner = _SteadyDriver(eyes="closed")
        blink = BlinkFilter(inner, interval_range=(0.0, 0.0), blink_duration=0.12)

        # Even with interval=0, the filter should NOT inject a second closed state
        # on top of an already-closed inner — it only blinks over "open".
        for _ in range(10):
            s = blink.poll(1.0)
            assert s.eyes == "closed"  # inner's closed, filter passes through

    def test_should_stop_delegates_to_inner(self):
        class _StoppingDriver(_SteadyDriver):
            def should_stop(self) -> bool:
                return True

        inner = _StoppingDriver()
        blink = BlinkFilter(inner)
        assert blink.should_stop() is True

    def test_close_delegates_to_inner(self):
        inner = _SteadyDriver()
        blink = BlinkFilter(inner)
        blink.close()
        assert inner.closed

    def test_blink_preserves_angle_and_mouth(self):
        """During a blink, angle and mouth from the inner state are preserved."""
        inner = _SteadyDriver(eyes="open")
        inner._state = DriverState(angle="left", eyes="open", mouth="smile")
        blink = BlinkFilter(inner, interval_range=(0.0, 0.0), blink_duration=0.5)

        blink.poll(0.0)  # fires blink
        s = blink.poll(0.1)
        assert s.eyes == "closed"
        assert s.angle == "left"
        assert s.mouth == "smile"
