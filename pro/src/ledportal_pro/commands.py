"""Keyboard-command handlers for the main capture loop.

Each handler takes ``(state, ctx)`` (see ``session.py``), mutates ``state``, and
returns a ``HandlerResult`` telling the loop what to do next. ``COMMAND_HANDLERS``
maps each :class:`InputCommand` to its handler, replacing what used to be a long
``if/elif cmd == ...`` chain in ``main()``.

Adding a command is now: write a ``handle_*`` function and add one table entry.
Almost every handler returns ``CONTINUE`` (the keypress is consumed and the next
frame is captured on the following tick). ``QUIT`` returns ``BREAK``; the manual-
demo start returns ``FALLTHROUGH`` so its first step is processed this tick.
"""

from __future__ import annotations

from collections.abc import Callable

from .exceptions import DeviceNotFoundError
from .processing import convert_to_rgb565, resize_frame
from .session import HandlerResult, LoopContext, SessionState
from .transport import create_transport
from .ui import (
    _ALGORITHM_LABELS,
    LED_SIZE_STEPS,
    AvatarCaptureManager,
    InputCommand,
    PreviewAlgorithm,
    print_help,
)

Handler = Callable[[SessionState, LoopContext], HandlerResult]


def _print_current_help(state: SessionState, ctx: LoopContext) -> None:
    """Render the help/status screen from current state (shared by several commands)."""
    print_help(
        state.orientation,
        state.processing_mode,
        state.black_and_white,
        state.debug_mode,
        state.zoom_level,
        ctx.config.ui.show_preview,
        state.mirror_mode,
        _ALGORITHM_LABELS[state.render_algorithm],
        state.led_size_pct,
    )


# --- Orientation -----------------------------------------------------------


def handle_orientation_landscape(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.orientation = "landscape"
    print("\n=== ORIENTATION: LANDSCAPE ===\n")
    return HandlerResult.CONTINUE


def handle_orientation_portrait(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.orientation = "portrait"
    print("\n=== ORIENTATION: PORTRAIT ===\n")
    return HandlerResult.CONTINUE


# --- Processing mode -------------------------------------------------------


def handle_processing_center(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.processing_mode = "center"
    print("\n=== PROCESSING: CENTER CROP ===\n")
    return HandlerResult.CONTINUE


def handle_processing_stretch(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.processing_mode = "stretch"
    print("\n=== PROCESSING: STRETCH ===\n")
    return HandlerResult.CONTINUE


def handle_processing_fit(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.processing_mode = "fit"
    print("\n=== PROCESSING: FIT (letterbox) ===\n")
    return HandlerResult.CONTINUE


# --- Effects ---------------------------------------------------------------


def handle_toggle_bw(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.black_and_white = not state.black_and_white
    mode_str = "BLACK & WHITE" if state.black_and_white else "COLOR"
    print(f"\n=== {mode_str} MODE ===\n")
    return HandlerResult.CONTINUE


def handle_toggle_mirror(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.mirror_mode = not state.mirror_mode
    mode_str = "ON" if state.mirror_mode else "OFF"
    print(f"\n=== MIRROR: {mode_str} ===\n")
    return HandlerResult.CONTINUE


def handle_cycle_render_algorithm(state: SessionState, ctx: LoopContext) -> HandlerResult:
    next_val = (state.render_algorithm.value + 1) % len(PreviewAlgorithm)
    state.render_algorithm = PreviewAlgorithm(next_val)
    print(f"\n=== RENDER ALGORITHM: {_ALGORITHM_LABELS[state.render_algorithm]} ===\n")
    return HandlerResult.CONTINUE


def handle_led_size_increase(state: SessionState, ctx: LoopContext) -> HandlerResult:
    if state.render_algorithm == PreviewAlgorithm.CIRCLES:
        idx = (
            LED_SIZE_STEPS.index(state.led_size_pct) if state.led_size_pct in LED_SIZE_STEPS else -1
        )
        if idx < len(LED_SIZE_STEPS) - 1:
            state.led_size_pct = LED_SIZE_STEPS[idx + 1]
        print(f"\n=== LED SIZE: {state.led_size_pct}% ===\n")
    else:
        print("\n=== LED SIZE: press 'o' to switch to Circles mode ===\n")
    return HandlerResult.CONTINUE


def handle_led_size_decrease(state: SessionState, ctx: LoopContext) -> HandlerResult:
    if state.render_algorithm == PreviewAlgorithm.CIRCLES:
        idx = (
            LED_SIZE_STEPS.index(state.led_size_pct) if state.led_size_pct in LED_SIZE_STEPS else -1
        )
        if idx > 0:
            state.led_size_pct = LED_SIZE_STEPS[idx - 1]
        print(f"\n=== LED SIZE: {state.led_size_pct}% ===\n")
    else:
        print("\n=== LED SIZE: press 'o' to switch to Circles mode ===\n")
    return HandlerResult.CONTINUE


def handle_zoom_toggle(state: SessionState, ctx: LoopContext) -> HandlerResult:
    # Cycle: 1.0 → 0.75 → 0.5 → 0.25 → 1.0
    if state.zoom_level == 1.0:
        state.zoom_level = 0.75
    elif state.zoom_level == 0.75:
        state.zoom_level = 0.5
    elif state.zoom_level == 0.5:
        state.zoom_level = 0.25
    else:
        state.zoom_level = 1.0

    zoom_pct = int(state.zoom_level * 100)
    print(f"\n=== ZOOM: {zoom_pct}% ===\n")
    return HandlerResult.CONTINUE


# --- Display / debug / preview ---------------------------------------------


def _reconnect_transport(state: SessionState, ctx: LoopContext) -> None:
    """Attempt to (re)connect the transport, printing status; sets None on failure."""
    try:
        state.transport = create_transport(ctx.config.transport)
        state.transport.connect(ctx.args.port)
        print(f"Connected to Matrix Portal on {state.transport.port}\n")
    except DeviceNotFoundError as e:
        print(f"Connection failed: {e}")
        print("!!! Press 't' to try again when the portal is connected. !!!\n")
        state.transport = None


def handle_toggle_display(state: SessionState, ctx: LoopContext) -> HandlerResult:
    if state.display_enabled and state.transport is None:
        # Already enabled but disconnected — reconnect without toggling to paused
        print("\n=== RECONNECTING TO MATRIX PORTAL ===")
        _reconnect_transport(state, ctx)
    else:
        state.display_enabled = not state.display_enabled
        if state.display_enabled:
            print("\n=== DISPLAY: ENABLED ===")
            if state.transport is None:
                print("Attempting to reconnect to Matrix Portal...")
                _reconnect_transport(state, ctx)
            else:
                print()
        else:
            print("\n=== DISPLAY: PAUSED (by user) — press 't' to resume ===\n")
    return HandlerResult.CONTINUE


def handle_toggle_debug(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.debug_mode = not state.debug_mode
    mode_str = "ON" if state.debug_mode else "OFF"
    print(f"\n=== DEBUG MODE: {mode_str} ===\n")
    return HandlerResult.CONTINUE


def handle_toggle_preview(state: SessionState, ctx: LoopContext) -> HandlerResult:
    ctx.config.ui.show_preview = not ctx.config.ui.show_preview
    if ctx.config.ui.show_preview:
        print("\n=== PREVIEW WINDOW: ENABLED ===\n")
    else:
        import cv2 as _cv2

        _cv2.destroyAllWindows()
        _cv2.waitKey(1)
        print("\n=== PREVIEW WINDOW: DISABLED ===\n")
    return HandlerResult.CONTINUE


# --- Demo ------------------------------------------------------------------


def handle_demo_toggle(state: SessionState, ctx: LoopContext) -> HandlerResult:
    # Reset to clean known state and start auto demo
    state.reset_view()
    ctx.demo.start_auto()
    print("\n=== DEMO MODE: AUTO (SPACE=pause, ./>=next, ,/<=prev, x=stop) ===\n")
    return HandlerResult.CONTINUE


def handle_demo_manual(state: SessionState, ctx: LoopContext) -> HandlerResult:
    # Reset to clean known state and start manual demo
    state.reset_view()
    ctx.demo.start_manual()
    demo_cmd = ctx.demo.next_step()
    state.demo_label = demo_cmd.label
    print("\n=== DEMO MODE: MANUAL (./>=next, ,/<=prev, x=stop) ===\n")
    print(
        f"--- Demo [{ctx.demo.step_position}]: {demo_cmd.description} ({ctx.demo.controls_hint}) ---"
    )
    # Original behavior: the first step's command is NOT re-dispatched (it was
    # assigned to a then-dead local). Only demo_label is applied; fall through
    # to render this tick so the label shows immediately.
    return HandlerResult.FALLTHROUGH


# --- System ----------------------------------------------------------------


def handle_reset(state: SessionState, ctx: LoopContext) -> HandlerResult:
    state.reset_view()
    state.debug_mode = False
    state.display_enabled = True
    print("\n=== RESET TO DEFAULTS ===")
    print(
        "Orientation=landscape, Processing=center, Color, Mirror=OFF, "
        "Algorithm=diffused panel emulation, Size=100%, Debug=OFF, Zoom=100%, Display=ON\n"
    )
    return HandlerResult.CONTINUE


def handle_help(state: SessionState, ctx: LoopContext) -> HandlerResult:
    _print_current_help(state, ctx)
    return HandlerResult.CONTINUE


def handle_quit(state: SessionState, ctx: LoopContext) -> HandlerResult:
    print("\n=== QUIT REQUESTED ===\n")
    return HandlerResult.BREAK


def handle_snapshot(state: SessionState, ctx: LoopContext) -> HandlerResult:
    # Imported lazily to avoid a circular import (main imports commands).
    from .main import run_snapshot_sequence

    if not state.save_enabled:
        print("  Snapshot saving disabled (--no-save)")
    elif not state.display_enabled and state.last_sent_frame is not None:
        # Paused: save the frozen frame on the device — no countdown
        print("  Saving paused frame...")
        frame_bytes_save = convert_to_rgb565(state.last_sent_frame)
        ctx.snapshot_manager.save(
            state.last_sent_frame, frame_bytes_save, state.orientation, debug_mode=state.debug_mode
        )
        print("  Saved.")
    else:
        run_snapshot_sequence(
            ctx.camera,
            state.transport,
            ctx.config,
            ctx.snapshot_manager,
            ctx.keyboard,
            state.black_and_white,
            state.orientation,
            state.processing_mode,
            state.zoom_level,
            state.debug_mode,
            state.mirror_mode,
            state.render_algorithm,
            state.led_size_pct,
        )
    ctx.keyboard.clear_buffer()
    return HandlerResult.CONTINUE


def handle_avatar(state: SessionState, ctx: LoopContext) -> HandlerResult:
    avatar_manager = AvatarCaptureManager()
    avatar_manager.run_capture_session(
        camera=ctx.camera,
        transport=state.transport,
        config=ctx.config,
        orientation=state.orientation,
        processing_mode=state.processing_mode,
        zoom_level=state.zoom_level,
        resize_fn=resize_frame,
        convert_fn=convert_to_rgb565,
    )
    ctx.keyboard.clear_buffer()
    return HandlerResult.CONTINUE


COMMAND_HANDLERS: dict[InputCommand, Handler] = {
    InputCommand.ORIENTATION_LANDSCAPE: handle_orientation_landscape,
    InputCommand.ORIENTATION_PORTRAIT: handle_orientation_portrait,
    InputCommand.PROCESSING_CENTER: handle_processing_center,
    InputCommand.PROCESSING_STRETCH: handle_processing_stretch,
    InputCommand.PROCESSING_FIT: handle_processing_fit,
    InputCommand.TOGGLE_BW: handle_toggle_bw,
    InputCommand.TOGGLE_MIRROR: handle_toggle_mirror,
    InputCommand.CYCLE_RENDER_ALGORITHM: handle_cycle_render_algorithm,
    InputCommand.LED_SIZE_INCREASE: handle_led_size_increase,
    InputCommand.LED_SIZE_DECREASE: handle_led_size_decrease,
    InputCommand.ZOOM_TOGGLE: handle_zoom_toggle,
    InputCommand.TOGGLE_DISPLAY: handle_toggle_display,
    InputCommand.TOGGLE_DEBUG: handle_toggle_debug,
    InputCommand.TOGGLE_PREVIEW: handle_toggle_preview,
    InputCommand.DEMO_TOGGLE: handle_demo_toggle,
    InputCommand.DEMO_MANUAL: handle_demo_manual,
    InputCommand.RESET: handle_reset,
    InputCommand.HELP: handle_help,
    InputCommand.QUIT: handle_quit,
    InputCommand.SNAPSHOT: handle_snapshot,
    InputCommand.AVATAR: handle_avatar,
}
