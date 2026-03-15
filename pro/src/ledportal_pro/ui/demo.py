"""Demo mode that automatically cycles through all display features."""

from dataclasses import dataclass

from .input import InputCommand


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
    """Automatically cycles through display features on a timer.

    Usage:
        demo = DemoMode()
        demo.start()
        while running:
            demo_cmd = demo.get_next_command(time.time())
            if demo_cmd is not None:
                # inject demo_cmd.command into the main loop
    """

    def __init__(self, step_duration: float = 3.0) -> None:
        """Initialize demo mode.

        Args:
            step_duration: Seconds to display each step (except snapshot).
        """
        self._step_duration = step_duration
        self._sequence = _build_sequence(step_duration)
        self._active = False
        self._step_index = 0
        self._step_start_time = 0.0

    @property
    def is_active(self) -> bool:
        """Whether demo mode is currently running."""
        return self._active

    def start(self) -> None:
        """Activate demo mode and reset to the first step."""
        self._active = True
        self._step_index = 0
        self._step_start_time = 0.0  # Force immediate first step on first check

    def stop(self) -> None:
        """Deactivate demo mode."""
        self._active = False

    def get_next_command(self, current_time: float) -> DemoCommand | None:
        """Check whether the current step's duration has elapsed.

        If elapsed, advances to the next step and returns the command to inject.
        Returns None if it is not yet time to advance.

        Args:
            current_time: Current time in seconds (e.g. time.time()).

        Returns:
            DemoCommand to inject, or None if no action needed yet.
        """
        if not self._active:
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
