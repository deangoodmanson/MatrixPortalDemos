"""Runtime state and context for the main capture loop.

Splits the ~14 mutable locals that used to live inside ``main()`` into a single
``SessionState`` object, and bundles the loop's collaborators into a frozen
``LoopContext``. Command handlers (see ``commands.py``) receive ``(state, ctx)``
and mutate ``state``, returning a ``HandlerResult`` to tell the loop whether to
skip to the next tick, render this frame, or exit.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray

from .capture import CameraBase
from .config import AppConfig
from .transport import TransportBase
from .ui import DemoMode, KeyboardHandler, PreviewAlgorithm, SnapshotManager
from .ui.overlay import LED_SIZE_DEFAULT


class HandlerResult(Enum):
    """What the main loop should do after a command handler runs.

    - ``CONTINUE``: the keypress was fully handled; skip this frame and poll again.
    - ``FALLTHROUGH``: state changed; proceed to capture/process/render this tick so
      the change is visible immediately (orientation, B&W, mirror, zoom, …).
    - ``BREAK``: exit the capture loop (quit).
    """

    CONTINUE = auto()
    FALLTHROUGH = auto()
    BREAK = auto()


@dataclass
class SessionState:
    """Mutable runtime state of the capture loop.

    Holds only true loop locals. Flags that belong to configuration
    (``show_preview``, ``auto_print``, …) stay on ``AppConfig`` and are read via
    ``LoopContext.config``.
    """

    # View settings (cycled by keyboard / demo)
    orientation: str
    processing_mode: str
    black_and_white: bool = False
    mirror_mode: bool = False
    zoom_level: float = 1.0  # 1.0 = 100%, 0.75 = 75%, etc.
    render_algorithm: PreviewAlgorithm = PreviewAlgorithm.GAUSSIAN_DIFFUSED
    led_size_pct: int = LED_SIZE_DEFAULT

    # Output / display
    display_enabled: bool = True  # User's intent to send to the device
    debug_mode: bool = False
    save_enabled: bool = True  # Whether snapshots may be saved to disk

    # Live loop state
    transport: TransportBase | None = None  # rebound on reconnect/disconnect
    last_sent_frame: NDArray[np.uint8] | None = None  # last successful send
    frame_count: int = 0
    display_status: str = "unknown"
    demo_label: str = ""  # current demo step label drawn on the frame

    def reset_view(self) -> None:
        """Restore the view settings to their defaults.

        Shared by RESET and the two demo-start commands, which all return to a
        clean known view before doing their own thing.
        """
        self.orientation = "landscape"
        self.processing_mode = "center"
        self.black_and_white = False
        self.mirror_mode = False
        self.zoom_level = 1.0
        self.render_algorithm = PreviewAlgorithm.GAUSSIAN_DIFFUSED
        self.led_size_pct = LED_SIZE_DEFAULT


@dataclass(frozen=True)
class LoopContext:
    """Immutable collaborators the command handlers need.

    The mutable ``transport`` is intentionally *not* here — it lives on
    ``SessionState`` because reconnect/disconnect paths rebind it. ``args`` is
    the parsed CLI namespace (e.g. ``args.port`` for reconnect).
    """

    config: AppConfig
    args: argparse.Namespace
    camera: CameraBase
    snapshot_manager: SnapshotManager
    keyboard: KeyboardHandler
    demo: DemoMode = field(default_factory=DemoMode)
