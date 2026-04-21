"""Driver protocol and shared state type for avatar expression control.

A Driver is anything that can emit a DriverState describing the subject's
current pose. Drivers are polled at each frame tick by AvatarLoop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class DriverState:
    """Semantic description of the avatar's desired pose.

    Any field may be ``None``, meaning "no change" — the resolver keeps the
    last resolved value. Partial updates are the common case (e.g. a keyboard
    driver might only update eyes, leaving mouth and angle as-is).
    """

    angle: str | None = None
    eyes: str | None = None
    mouth: str | None = None


@runtime_checkable
class Driver(Protocol):
    """Anything that can feed the avatar loop with pose updates."""

    def poll(self, dt: float) -> DriverState:
        """Return the current desired state.

        Args:
            dt: Elapsed seconds since the last poll call.

        Returns:
            A DriverState — any field may be None for "no change".
        """
        ...

    def should_stop(self) -> bool:
        """Return True when the loop should exit cleanly."""
        ...

    def close(self) -> None:
        """Release any resources held by the driver."""
        ...
