"""AvatarLoop: the main render loop, and BlinkFilter driver middleware.

AvatarLoop ties together a Driver, VariantResolver, and AvatarPlayer into a
blocking run loop that targets a fixed frame rate.

BlinkFilter wraps any Driver and injects brief "eyes=closed" states at random
intervals, simulating natural blinking.
"""

from __future__ import annotations

import random
import time

from .drivers import Driver, DriverState
from .player import AvatarPlayer
from .resolver import VariantResolver


class AvatarLoop:
    """Blocking render loop that polls a driver and drives the avatar player.

    Args:
        player: The compositor that renders and sends frames.
        driver: Source of DriverState updates.
        resolver: Maps semantic states to concrete variant names.
        target_fps: Desired frame rate (default 15).
    """

    def __init__(
        self,
        player: AvatarPlayer,
        driver: Driver,
        resolver: VariantResolver,
        target_fps: float = 15.0,
    ) -> None:
        self._player = player
        self._driver = driver
        self._resolver = resolver
        self._frame_budget = 1.0 / target_fps

    def run(self) -> None:
        """Block until the driver stops or KeyboardInterrupt.

        Always calls ``driver.close()`` on exit.
        """
        try:
            prev = time.monotonic()
            while not self._driver.should_stop():
                now = time.monotonic()
                dt = now - prev
                prev = now

                state = self._driver.poll(dt)
                changes = self._resolver.resolve(state)
                for feature, variant in changes.items():
                    try:
                        self._player.set_state(feature, variant)
                    except KeyError:
                        pass  # variant not in asset; resolver fallback was best effort

                self._player.send_frame()

                elapsed = time.monotonic() - now
                remaining = self._frame_budget - elapsed
                if remaining > 0:
                    time.sleep(remaining)
        except KeyboardInterrupt:
            pass
        finally:
            self._driver.close()


class BlinkFilter:
    """Driver middleware that injects automatic eye blinks.

    Wraps any Driver. When the inner driver's eyes are ``"open"``, the filter
    briefly overrides to ``"closed"`` at randomised intervals. When the inner
    driver already has eyes closed (e.g. expression), blink injection is
    suppressed.

    Conforms to the Driver protocol — compose as ``BlinkFilter(KeyboardDriver())``.

    Args:
        inner: The wrapped driver.
        interval_range: ``(min_s, max_s)`` seconds between blink starts.
        blink_duration: How long (seconds) the "eyes=closed" override lasts.
    """

    def __init__(
        self,
        inner: Driver,
        interval_range: tuple[float, float] = (3.0, 7.0),
        blink_duration: float = 0.12,
    ) -> None:
        self._inner = inner
        self._interval_range = interval_range
        self._blink_duration = blink_duration

        self._blink_timer = 0.0
        self._next_blink = random.uniform(*interval_range)
        self._is_blinking = False
        self._blink_remaining = 0.0

    # ------------------------------------------------------------------ #
    # Driver protocol                                                      #
    # ------------------------------------------------------------------ #

    def poll(self, dt: float) -> DriverState:
        inner_state = self._inner.poll(dt)

        if self._is_blinking:
            self._blink_remaining -= dt
            if self._blink_remaining <= 0:
                self._is_blinking = False
                self._next_blink = random.uniform(*self._interval_range)
                self._blink_timer = 0.0
            else:
                return DriverState(
                    angle=inner_state.angle,
                    eyes="closed",
                    mouth=inner_state.mouth,
                )
        else:
            inner_eyes = inner_state.eyes
            if inner_eyes is None or inner_eyes == "open":
                self._blink_timer += dt
                if self._blink_timer >= self._next_blink:
                    self._is_blinking = True
                    self._blink_remaining = self._blink_duration

        return inner_state

    def should_stop(self) -> bool:
        return self._inner.should_stop()

    def close(self) -> None:
        self._inner.close()
