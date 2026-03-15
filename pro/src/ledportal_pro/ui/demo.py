"""Demo mode that automatically cycles through all display features."""

from dataclasses import dataclass
from enum import Enum, auto

from .input import InputCommand


class DemoState(Enum):
    """Demo mode states."""

    OFF = auto()
    AUTO = auto()  # Timed auto-advance
    PAUSED = auto()  # Auto was running, now paused on current step
    MANUAL = auto()  # Navigate-only, no auto-advance


@dataclass
class DemoStep:
    """A single step in the demo sequence."""

    command: InputCommand
    description: str
    duration: float
    label: str  # Short label drawn on the device frame (fits 64px wide)


@dataclass
class DemoCommand:
    """Command returned by get_next_command when a step fires."""

    command: InputCommand
    description: str
    label: str  # Short label for on-device overlay


def _effects_steps(step_duration: float) -> list[DemoStep]:
    """Return the processing and effects steps (orientation-independent).

    Args:
        step_duration: Seconds to display each step.

    Returns:
        List of DemoStep objects for one orientation pass.
    """
    return [
        DemoStep(InputCommand.PROCESSING_STRETCH, "Stretch processing", step_duration, "Stretch"),
        DemoStep(InputCommand.PROCESSING_FIT, "Fit processing", step_duration, "Fit"),
        DemoStep(
            InputCommand.PROCESSING_CENTER, "Center processing (restore)", step_duration, "Center"
        ),
        DemoStep(InputCommand.TOGGLE_BW, "B&W on", step_duration, "B&W"),
        DemoStep(InputCommand.TOGGLE_BW, "B&W off (restore)", step_duration, "Color"),
        DemoStep(InputCommand.TOGGLE_MIRROR, "Mirror on", step_duration, "Mirror"),
        DemoStep(InputCommand.TOGGLE_MIRROR, "Mirror off (restore)", step_duration, "No Mirror"),
        DemoStep(InputCommand.ZOOM_TOGGLE, "Zoom 75%", step_duration, "Zoom 75%"),
        DemoStep(InputCommand.ZOOM_TOGGLE, "Zoom 50%", step_duration, "Zoom 50%"),
        DemoStep(InputCommand.ZOOM_TOGGLE, "Zoom 25%", step_duration, "Zoom 25%"),
        DemoStep(InputCommand.ZOOM_TOGGLE, "Zoom 100% (restore)", step_duration, "Zoom 100%"),
    ]


def _preview_steps(step_duration: float) -> list[DemoStep]:
    """Return steps that cycle through preview algorithms and circle sizes.

    Starting from the default (Gaussian Diffused), cycles through all four
    algorithms. When on Circles, also cycles through size steps to showcase
    the range. Restores defaults (Gaussian Diffused, Size=100%) at the end.

    Args:
        step_duration: Seconds to display each step.

    Returns:
        List of DemoStep objects for the preview algorithm tour.
    """
    return [
        # From default (Gaussian Diffused) → Squares
        DemoStep(InputCommand.CYCLE_RENDER_ALGORITHM, "Squares", step_duration, "Squares"),
        # Squares → Circles (default size=100%)
        DemoStep(
            InputCommand.CYCLE_RENDER_ALGORITHM,
            "Circles Size=100%",
            step_duration,
            "Circle 100%",
        ),
        # Cycle through circle sizes: 100→125→150→25→50→75
        DemoStep(InputCommand.LED_SIZE_INCREASE, "Circles Size=125%", step_duration, "Circle 125%"),
        DemoStep(InputCommand.LED_SIZE_INCREASE, "Circles Size=150%", step_duration, "Circle 150%"),
        DemoStep(InputCommand.LED_SIZE_DECREASE, "Circles Size=125%", step_duration, "Circle 125%"),
        DemoStep(InputCommand.LED_SIZE_DECREASE, "Circles Size=100%", step_duration, "Circle 100%"),
        DemoStep(InputCommand.LED_SIZE_DECREASE, "Circles Size=75%", step_duration, "Circle 75%"),
        DemoStep(InputCommand.LED_SIZE_DECREASE, "Circles Size=50%", step_duration, "Circle 50%"),
        DemoStep(InputCommand.LED_SIZE_DECREASE, "Circles Size=25%", step_duration, "Circle 25%"),
        # Restore size to default (100%): 25→50→75→100
        DemoStep(InputCommand.LED_SIZE_INCREASE, "Circles Size=50%", 0.0, ""),
        DemoStep(InputCommand.LED_SIZE_INCREASE, "Circles Size=75%", 0.0, ""),
        DemoStep(InputCommand.LED_SIZE_INCREASE, "Circles Size=100%", 0.0, ""),
        # Circles → Gaussian Raw
        DemoStep(
            InputCommand.CYCLE_RENDER_ALGORITHM,
            "Raw panel emulation",
            step_duration,
            "Gaussian Raw",
        ),
        # Gaussian Raw → Gaussian Diffused (restore default)
        DemoStep(
            InputCommand.CYCLE_RENDER_ALGORITHM,
            "Diffused panel emulation (restore)",
            step_duration,
            "Gaussian Diff",
        ),
    ]


def _build_sequence(step_duration: float) -> list[DemoStep]:
    """Construct the full demo sequence: all effects in landscape, then portrait.

    Args:
        step_duration: Seconds to display each step.

    Returns:
        List of DemoStep objects in order.
    """
    return [
        # --- Landscape pass ---
        DemoStep(
            InputCommand.ORIENTATION_LANDSCAPE, "Landscape orientation", step_duration, "Landscape"
        ),
        *_preview_steps(step_duration),
        *_effects_steps(step_duration),
        # --- Portrait pass ---
        DemoStep(
            InputCommand.ORIENTATION_PORTRAIT, "Portrait orientation", step_duration, "Portrait"
        ),
        *_effects_steps(step_duration),
    ]


class DemoMode:
    """Cycles through display features automatically or via manual navigation.

    Supports three active states:
    - AUTO: steps advance on a timer (press space to pause)
    - PAUSED: auto-advance is frozen on the current step (space to resume)
    - MANUAL: no timer, navigate with next/prev only

    Usage:
        demo = DemoMode()
        demo.start_auto()   # or demo.start_manual()
        while running:
            demo_cmd = demo.get_next_command(time.time())
            if demo_cmd is not None:
                # inject demo_cmd.command into the main loop
    """

    def __init__(self, step_duration: float = 3.0) -> None:
        """Initialize demo mode.

        Args:
            step_duration: Seconds to display each step.
        """
        self._step_duration = step_duration
        self._sequence = _build_sequence(step_duration)
        self._state = DemoState.OFF
        self._step_index = 0
        self._step_start_time = 0.0

    @property
    def state(self) -> DemoState:
        """Current demo state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Whether demo mode is running (any state except OFF)."""
        return self._state != DemoState.OFF

    @property
    def step_position(self) -> str:
        """Current step position as 'N/Total' string."""
        return f"{self._step_index + 1}/{len(self._sequence)}"

    @property
    def controls_hint(self) -> str:
        """Short controls reminder string based on current state."""
        if self._state == DemoState.AUTO:
            return "SPACE=pause, ./>=next, ,/<=prev, x=stop"
        if self._state == DemoState.PAUSED:
            return "SPACE=resume, ./>=next, ,/<=prev, x=stop"
        if self._state == DemoState.MANUAL:
            return "./>=next, ,/<=prev, x=stop"
        return ""

    def start_auto(self) -> None:
        """Start demo in auto-advance mode, reset to first step."""
        self._state = DemoState.AUTO
        self._step_index = 0
        self._step_start_time = 0.0

    def start_manual(self) -> None:
        """Start demo in manual navigation mode, reset to first step."""
        self._state = DemoState.MANUAL
        self._step_index = 0
        self._step_start_time = 0.0

    def stop(self) -> None:
        """Deactivate demo mode."""
        self._state = DemoState.OFF

    def pause(self) -> None:
        """Pause auto-advance (keeps current step visible)."""
        if self._state == DemoState.AUTO:
            self._state = DemoState.PAUSED

    def resume(self) -> None:
        """Resume auto-advance from current step."""
        if self._state == DemoState.PAUSED:
            self._state = DemoState.AUTO
            self._step_start_time = 0.0

    def toggle_pause(self) -> DemoState:
        """Toggle between AUTO and PAUSED. Returns new state."""
        if self._state == DemoState.AUTO:
            self.pause()
        elif self._state == DemoState.PAUSED:
            self.resume()
        return self._state

    def next_step(self) -> DemoCommand:
        """Advance to the next step and return its command.

        In AUTO mode, also resets the timer so the step gets its full duration.
        """
        step = self._sequence[self._step_index]
        fired = DemoCommand(command=step.command, description=step.description, label=step.label)
        self._step_index = (self._step_index + 1) % len(self._sequence)
        self._step_start_time = 0.0
        return fired

    def prev_step(self) -> DemoCommand:
        """Go back to the previous step and return its command.

        Wraps around to the last step if at the beginning.
        In AUTO mode, also resets the timer so the step gets its full duration.
        """
        self._step_index = (self._step_index - 2) % len(self._sequence)
        step = self._sequence[self._step_index]
        fired = DemoCommand(command=step.command, description=step.description, label=step.label)
        self._step_index = (self._step_index + 1) % len(self._sequence)
        self._step_start_time = 0.0
        return fired

    def get_next_command(self, current_time: float) -> DemoCommand | None:
        """Check whether the current step's duration has elapsed (AUTO mode only).

        In PAUSED or MANUAL mode, always returns None (use next_step/prev_step
        for navigation).

        Args:
            current_time: Current time in seconds (e.g. time.time()).

        Returns:
            DemoCommand to inject, or None if no action needed yet.
        """
        if self._state != DemoState.AUTO:
            return None

        step = self._sequence[self._step_index]

        # _step_start_time == 0.0 signals "fire immediately"
        if self._step_start_time != 0.0 and current_time - self._step_start_time < step.duration:
            return None

        # Fire the current step
        fired = DemoCommand(command=step.command, description=step.description, label=step.label)

        # Advance to the next step (looping)
        self._step_index = (self._step_index + 1) % len(self._sequence)
        self._step_start_time = current_time

        return fired
