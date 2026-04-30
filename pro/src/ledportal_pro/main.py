#!/usr/bin/env python3
"""Main entry point for LED Portal Pro."""

import argparse
import sys
import time
from pathlib import Path

from .capture import create_camera
from .capture.factory import list_available_cameras
from .config import AppConfig, load_config
from .exceptions import CameraCaptureFailed, DeviceNotFoundError, LEDPortalError
from .processing import (
    apply_brightness_limit,
    apply_grayscale,
    apply_mirror,
    apply_zoom_crop,
    convert_to_rgb565,
    create_test_pattern,
    resize_frame,
)
from .transport import create_transport
from .ui import (
    _ALGORITHM_LABELS,
    LED_SIZE_DEFAULT,
    LED_SIZE_STEPS,
    AvatarCaptureManager,
    DemoMode,
    DemoState,
    InputCommand,
    KeyboardHandler,
    PreviewAlgorithm,
    SnapshotManager,
    draw_border,
    draw_countdown_overlay,
    draw_text_overlay,
    print_help,
    show_preview,
    speak,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="LED Portal Pro - Camera feed for LED matrix display",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--frames",
        "-n",
        type=int,
        default=0,
        help="Number of frames to capture (0 for infinite)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Start with display output paused (toggle with 't' key)",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=None,
        help="Camera index to use (overrides config)",
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port to use (overrides auto-detection)",
    )
    parser.add_argument(
        "--bw",
        action="store_true",
        help="Start in black and white mode",
    )
    parser.add_argument(
        "--orientation",
        choices=["landscape", "portrait"],
        default=None,
        help="Display orientation (overrides config)",
    )
    parser.add_argument(
        "--processing",
        choices=["center", "stretch", "fit"],
        default=None,
        help="Processing mode (overrides config)",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable debug/stats output (toggle with 'd' key)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Disable saving snapshots to disk (countdown still runs)",
    )

    # A0 hardware snap button (reads "SNAP" from the device console serial port)
    snap_group = parser.add_mutually_exclusive_group()
    snap_group.add_argument(
        "--a0-snap",
        action="store_true",
        default=None,
        help="Enable A0 hardware snap button (overrides config; requires --console-port or console_port in config)",
    )
    snap_group.add_argument(
        "--no-a0-snap",
        action="store_true",
        help="Disable A0 hardware snap button (overrides config; releases console port for REPL access)",
    )
    parser.add_argument(
        "--console-port",
        type=str,
        default=None,
        metavar="PORT",
        help="Matrix Portal CDC console serial port for A0 snap (e.g. /dev/ttyACM0 or /dev/cu.usbmodem14101)",
    )

    return parser.parse_args()


def run_snapshot_sequence(
    camera: object,
    transport: object | None,
    config: AppConfig,
    snapshot_manager: SnapshotManager,
    keyboard: KeyboardHandler,
    black_and_white: bool,
    orientation: str,
    processing_mode: str,
    zoom_level: float,
    debug_mode: bool = False,
    mirror: bool = False,
    render_algorithm: PreviewAlgorithm = PreviewAlgorithm.SQUARES,
    led_size_pct: int = LED_SIZE_DEFAULT,
) -> bool:
    """Run the snapshot countdown and capture sequence.

    Args:
        camera: Camera instance.
        transport: Transport instance (may be None).
        config: Application configuration.
        snapshot_manager: Snapshot manager instance.
        keyboard: Keyboard handler for abort detection.
        black_and_white: Whether to apply grayscale filter.
        orientation: Current orientation (landscape/portrait).
        processing_mode: Current processing mode (center/stretch/fit).
        zoom_level: Current zoom level (0.25-1.0).
        debug_mode: Whether to save debug files alongside snapshot.
        mirror: Whether to apply horizontal mirror flip.
        render_algorithm: Current LED preview render algorithm.
        led_size_pct: Current LED size percentage.

    Returns:
        True if snapshot completed, False if aborted.
    """
    print("\n=== SNAPSHOT MODE (press any key to cancel) ===")
    print(f"Countdown: 3... 2... 1... ({config.ui.countdown_duration}s each)")
    speak("Get ready")

    from .capture.base import CameraBase

    camera_typed = camera if isinstance(camera, CameraBase) else None
    if camera_typed is None:
        print("Error: Invalid camera type")
        return False

    # Countdown with overlay
    last_small_frame = None
    last_original_frame = None

    for countdown in [3, 2, 1]:
        print(f"  Showing: {countdown}", flush=True)
        countdown_start = time.time()

        while time.time() - countdown_start < config.ui.countdown_duration:
            # Check for abort
            if keyboard.check_abort():
                print("\n=== SNAPSHOT CANCELLED ===\n")
                speak("Cancelled")
                keyboard.clear_buffer()
                return False

            try:
                original_frame = camera_typed.capture()
            except CameraCaptureFailed:
                continue

            # Apply zoom (keep original_frame pre-zoom for the preview left pane)
            frame = original_frame
            if zoom_level < 1.0:
                frame = apply_zoom_crop(frame, zoom_level)

            small_frame = resize_frame(
                frame, config.matrix, config.processing, orientation, processing_mode
            )
            if mirror:
                small_frame = apply_mirror(small_frame, orientation)
            if black_and_white:
                small_frame = apply_grayscale(small_frame)

            # Save the last frame from countdown "1" for the snapshot
            if countdown == 1:
                last_small_frame = small_frame.copy()
                last_original_frame = original_frame.copy()
                # Show blue border during "1" countdown to indicate capture framing
                small_frame = draw_border(small_frame, color=(255, 0, 0))  # Blue in BGR

            overlay_frame = draw_countdown_overlay(
                small_frame, countdown, config.matrix, orientation=orientation
            )
            frame_bytes = convert_to_rgb565(overlay_frame)

            if transport is not None:
                from .transport.base import TransportBase

                if isinstance(transport, TransportBase):
                    try:
                        transport.send_frame(frame_bytes)
                    except Exception:
                        pass

            if config.ui.show_preview:
                show_preview(
                    original_frame,
                    overlay_frame,
                    config.matrix,
                    orientation,
                    processing_mode,
                    zoom_level,
                    render_algorithm,
                    led_size_pct,
                    config.processing.max_brightness,
                )

            time.sleep(0.01)

    # Use the last frame from countdown "1" as the snapshot
    print("SNAP!")
    speak("Got it")

    if last_small_frame is None:
        print("Failed to capture snapshot frame")
        return False

    try:
        # Use the saved frame from countdown "1"
        small_frame = last_small_frame

        # Save the clean frame (no border)
        frame_bytes = convert_to_rgb565(small_frame)
        snapshot_path, debug_path, rgb565_path, pdf_path = snapshot_manager.save(
            small_frame,
            frame_bytes,
            orientation,
            debug_mode=debug_mode,
            original_frame=last_original_frame,
            render_algorithm=render_algorithm,
            led_size_pct=led_size_pct,
        )
        print(f"\n{'=' * 60}")
        print("SNAPSHOT SAVED:")
        print(f"  Snapshot: {snapshot_path}")
        if pdf_path:
            print(f"  PDF: {pdf_path}")
        if debug_mode:
            if debug_path:
                print(f"  Debug raw: {debug_path}")
            if rgb565_path:
                print(f"  Debug RGB565: {rgb565_path}")
        print(f"{'=' * 60}\n")

        # Show blue border on the matrix display only
        if transport is not None:
            from .transport.base import TransportBase

            if isinstance(transport, TransportBase):
                try:
                    bordered_frame = draw_border(small_frame, color=(255, 0, 0))  # Blue in BGR
                    transport.send_frame(convert_to_rgb565(bordered_frame))
                except Exception:
                    pass

        # Pause (can be aborted)
        pause_duration = int(config.ui.snapshot_pause_duration)
        print(f"Pausing for {pause_duration} seconds (press any key to skip)...")
        print("Resuming in: ", end="", flush=True)
        for i in range(pause_duration, 0, -1):
            if keyboard.check_abort():
                print(" Resuming now!\n")
                keyboard.clear_buffer()
                return True
            print(f"{i}... ", end="", flush=True)
            time.sleep(1)
        print("GO!\n")

    except CameraCaptureFailed:
        print("Failed to capture snapshot frame")

    return True


def instant_snapshot(
    last_sent_frame: object,
    transport: object | None,
    snapshot_manager: SnapshotManager,
    orientation: str,
    debug_mode: bool = False,
    render_algorithm: PreviewAlgorithm = PreviewAlgorithm.SQUARES,
    led_size_pct: int = LED_SIZE_DEFAULT,
) -> None:
    """Save an instant snapshot from the last frame sent to the device.

    Triggered by the A0 hardware snap button on the Matrix Portal.  Uses the
    cached last-sent frame so there is no 3-2-1 countdown delay and no new
    camera capture — the saved image exactly matches what the device displayed
    when the button was pressed (drift < one frame period, typically < 50 ms).

    Args:
        last_sent_frame: The last processed frame sent to the device (numpy array).
        transport: Transport instance for showing a brief confirmation flash.
        snapshot_manager: Snapshot manager instance.
        orientation: Current orientation (landscape/portrait).
        debug_mode: Whether to save debug files alongside snapshot.
        render_algorithm: Current LED preview render algorithm.
        led_size_pct: Current LED size percentage.
    """
    import numpy as np

    if not isinstance(last_sent_frame, np.ndarray):
        print("  A0 SNAP: no frame available yet — waiting for first frame")
        return

    print("\n=== A0 SNAP (hardware button) ===")
    speak("Got it")

    try:
        frame_bytes = convert_to_rgb565(last_sent_frame)
        snapshot_path, debug_path, rgb565_path, pdf_path = snapshot_manager.save(
            last_sent_frame,
            frame_bytes,
            orientation,
            debug_mode=debug_mode,
            render_algorithm=render_algorithm,
            led_size_pct=led_size_pct,
        )

        print(f"\n{'=' * 60}")
        print("SNAPSHOT SAVED (A0 hardware button):")
        print(f"  Snapshot: {snapshot_path}")
        if pdf_path:
            print(f"  PDF: {pdf_path}")
        if debug_mode:
            if debug_path:
                print(f"  Debug raw: {debug_path}")
            if rgb565_path:
                print(f"  Debug RGB565: {rgb565_path}")
        print(f"{'=' * 60}\n")

        # Brief blue border flash on the device to confirm capture
        if transport is not None:
            from .transport.base import TransportBase

            if isinstance(transport, TransportBase):
                try:
                    bordered = draw_border(last_sent_frame, color=(255, 0, 0))
                    transport.send_frame(convert_to_rgb565(bordered))
                except Exception:
                    pass

    except Exception as e:
        print(f"  A0 SNAP failed: {e}")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    args = parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except LEDPortalError as e:
        print(f"Configuration error: {e}")
        return 1

    # Override config with command line args
    if args.camera is not None:
        config.camera.index = args.camera
    if args.orientation is not None:
        config.processing.orientation = args.orientation
    if args.processing is not None:
        config.processing.processing_mode = args.processing
    if args.no_a0_snap:
        config.a0_snap_button = False
    elif args.a0_snap:
        config.a0_snap_button = True
    if args.console_port is not None:
        config.console_port = args.console_port

    # Print startup info
    print("LED Portal Pro v0.2.0")
    print(f"Matrix: {config.matrix.width}x{config.matrix.height}")
    print(f"Target FPS: {config.target_fps}")
    print(f"Frame size: {config.frame_size_bytes} bytes (RGB565)")
    if args.frames > 0:
        print(f"Will capture {args.frames} frames and exit")
    print()

    # List available cameras
    print("Detecting cameras...")
    available_cameras = list_available_cameras()
    if available_cameras:
        print(f"Found {len(available_cameras)} camera(s):")
        for cam in available_cameras:
            cam_type = cam.get("type", "unknown")
            index = cam.get("index", "?")
            backend = cam.get("backend", "unknown")
            resolution = cam.get("resolution", "unknown")
            fps = cam.get("fps", "unknown")
            name = cam.get("name", cam.get("model", f"Camera {index}"))
            print(
                f"  [{index}] {name} ({cam_type}/{backend}) - {resolution} @ {fps} fps (driver-reported)"
            )
    else:
        print("  No cameras detected (will try to open anyway)")
    print()

    # Initialize state
    camera = None
    transport = None
    console_serial = None  # CDC console port for A0 hardware snap button
    black_and_white = args.bw
    orientation = config.processing.orientation
    processing_mode = config.processing.processing_mode
    debug_mode = config.ui.debug_mode and not args.no_debug
    zoom_level = 1.0  # 1.0 = 100%, 0.75 = 75%, etc.
    mirror_mode = False  # Horizontal flip (mirror effect)
    render_algorithm = (
        PreviewAlgorithm.GAUSSIAN_DIFFUSED
    )  # LED preview render algorithm (cycles with 'o')
    led_size_pct = LED_SIZE_DEFAULT  # LED size percentage (only for CIRCLES)
    save_enabled = not args.no_save  # Whether to save snapshots to disk
    display_enabled = not args.no_display  # User's intent to send to display
    display_status = "unknown"  # Current display status with reason
    last_sent_frame = None  # Last frame successfully delivered to the device
    demo = DemoMode()  # Automatic feature cycling demo mode
    demo_label: str = ""  # Current step label drawn on the device frame

    try:
        # Setup camera
        camera = create_camera(config.camera)
        camera.open()

        # Display camera info
        cam_info = camera.get_camera_info()
        print("=" * 60)
        print("CAMERA INFORMATION:")
        print("=" * 60)
        print(f"  Type: {cam_info.get('type', 'unknown')}")
        if "index" in cam_info:
            print(f"  Index: {cam_info['index']}")
        if "backend" in cam_info:
            print(f"  Backend: {cam_info['backend']}")
        if "model" in cam_info:
            print(f"  Model: {cam_info['model']}")
        print(f"  Resolution: {cam_info.get('resolution', 'unknown')}")
        if "fps" in cam_info:
            print(f"  FPS (driver-reported): {cam_info['fps']} — camera driver reported speed.")
        if "format" in cam_info and cam_info["format"] != "unknown":
            print(f"  Format: {cam_info['format']}")
        if "requested_resolution" in cam_info:
            print(f"  Requested: {cam_info['requested_resolution']}")
        if "sensor_modes" in cam_info:
            print(f"  Sensor modes: {cam_info['sensor_modes']}")
        print("=" * 60)
        print()

        # Setup transport
        transport = create_transport(config.transport)
        try:
            transport.connect(args.port)
            print(f"Connected to Matrix Portal on {transport.port}")

            # Send test patterns to verify connection (only if display enabled)
            if display_enabled:
                test_pattern = create_test_pattern(config.matrix)
                # Only send 2 test frames (reduced from 5) to minimize power draw
                # during initial connection when matrix may be USB-powered only
                for i in range(2):
                    bytes_sent = transport.send_frame(test_pattern)
                    print(f"Test pattern {i + 1} sent: {bytes_sent} bytes")
                    time.sleep(0.5)  # Longer delay to avoid power spikes
                print("Verification frames sent.")
            else:
                print("Display paused (--no-display flag). Press 't' to enable.")
        except DeviceNotFoundError as e:
            print(f"Warning: {e}")
            print("Display paused (device not found). Press 't' to retry.")
            transport = None

        # Setup UI components
        snapshot_manager = SnapshotManager()

        # Open console port for A0 hardware snap button (if configured)
        if config.a0_snap_button and config.console_port:
            from .transport.serial import open_console_port

            try:
                console_serial = open_console_port(config.console_port)
                print(f"A0 snap button enabled — console port: {config.console_port}")
                print("  NOTE: REPL/terminal access to the device is suspended while running.")
                print("  Use --no-a0-snap or set a0_snap_button: false to restore REPL access.")
            except Exception as e:
                print(f"Warning: Could not open console port {config.console_port}: {e}")
                print("  A0 snap button disabled.  Check console_port in config.")
        elif config.a0_snap_button and not config.console_port:
            print("A0 snap button enabled in config but console_port is not set — feature inactive.")
            print("  Set console_port in your YAML or use --console-port PORT to activate.")

        print()
        print("Starting capture loop...")
        print_help(
            orientation,
            processing_mode,
            black_and_white,
            debug_mode,
            zoom_level,
            config.ui.show_preview,
            mirror_mode,
            _ALGORITHM_LABELS[render_algorithm],
            led_size_pct,
        )
        print("Starting — capturing and sending frames to Matrix Portal...")
        if transport is None:
            print("\n!!! Matrix Portal not connected — press 't' to connect when ready. !!!\n")

        # Main loop with keyboard handler context manager
        with KeyboardHandler(single_keypress=config.ui.single_keypress) as keyboard:
            frame_count = 0
            start_time = time.time()
            frame_time = 1.0 / config.target_fps

            while True:
                loop_start = time.time()

                # Check for keyboard input
                input_result = keyboard.check_input()
                cmd = input_result.command

                # Poll A0 hardware snap button via console port
                if console_serial is not None and console_serial.is_open:
                    try:
                        while console_serial.in_waiting > 0:
                            line = console_serial.readline().decode("utf-8", errors="ignore").strip()
                            if line == "SNAP" and save_enabled:
                                instant_snapshot(
                                    last_sent_frame,
                                    transport,
                                    snapshot_manager,
                                    orientation,
                                    debug_mode=debug_mode,
                                    render_algorithm=render_algorithm,
                                    led_size_pct=led_size_pct,
                                )
                            elif line == "SNAP" and not save_enabled:
                                print("  A0 SNAP received but snapshot saving disabled (--no-save)")
                    except Exception:
                        pass  # Serial errors don't crash the main loop

                # Demo mode input handling
                if demo.is_active:
                    if cmd == InputCommand.DEMO_NEXT:
                        demo_cmd = demo.next_step()
                        print(
                            f"\n--- Demo [{demo.step_position}]: {demo_cmd.description} ({demo.controls_hint}) ---"
                        )
                        cmd = demo_cmd.command
                        demo_label = demo_cmd.label
                    elif cmd == InputCommand.DEMO_PREV:
                        demo_cmd = demo.prev_step()
                        print(
                            f"\n--- Demo [{demo.step_position}]: {demo_cmd.description} ({demo.controls_hint}) ---"
                        )
                        cmd = demo_cmd.command
                        demo_label = demo_cmd.label
                    elif cmd == InputCommand.SNAPSHOT and demo.state == DemoState.MANUAL:
                        # Space is not meaningful in manual demo — ignore rather than stopping demo
                        continue
                    elif cmd == InputCommand.SNAPSHOT and demo.state in (
                        DemoState.AUTO,
                        DemoState.PAUSED,
                    ):
                        # Space pauses/resumes auto demo instead of taking snapshot
                        new_state = demo.toggle_pause()
                        if new_state == DemoState.PAUSED:
                            print(
                                f"\n=== DEMO: PAUSED [{demo.step_position}] "
                                f"({demo.controls_hint}) ===\n"
                            )
                        else:
                            print("\n=== DEMO: RESUMED (auto-advance) ===\n")
                        continue
                    elif cmd == InputCommand.DEMO_TOGGLE:
                        demo.stop()
                        demo_label = ""
                        print("\n=== DEMO MODE: OFF ===\n")
                        print_help(
                            orientation,
                            processing_mode,
                            black_and_white,
                            debug_mode,
                            zoom_level,
                            config.ui.show_preview,
                            mirror_mode,
                            _ALGORITHM_LABELS[render_algorithm],
                            led_size_pct,
                        )
                        continue
                    elif cmd == InputCommand.DEMO_MANUAL:
                        # Already active — ignore X while in demo
                        continue
                    elif cmd != InputCommand.NONE:
                        # Any other keypress stops demo
                        demo.stop()
                        demo_label = ""
                        print("\n=== DEMO MODE: STOPPED ===\n")
                        print_help(
                            orientation,
                            processing_mode,
                            black_and_white,
                            debug_mode,
                            zoom_level,
                            config.ui.show_preview,
                            mirror_mode,
                            _ALGORITHM_LABELS[render_algorithm],
                            led_size_pct,
                        )
                        # cmd falls through to normal handling below
                    else:
                        # No keypress — check auto-advance timer
                        demo_cmd = demo.get_next_command(time.time())
                        if demo_cmd is not None:
                            print(
                                f"\n--- Demo [{demo.step_position}]: {demo_cmd.description} ({demo.controls_hint}) ---"
                            )
                            cmd = demo_cmd.command
                            demo_label = demo_cmd.label

                # Handle orientation changes
                if cmd == InputCommand.ORIENTATION_LANDSCAPE:
                    orientation = "landscape"
                    print("\n=== ORIENTATION: LANDSCAPE ===\n")
                    continue
                elif cmd == InputCommand.ORIENTATION_PORTRAIT:
                    orientation = "portrait"
                    print("\n=== ORIENTATION: PORTRAIT ===\n")
                    continue

                # Handle processing mode changes
                elif cmd == InputCommand.PROCESSING_CENTER:
                    processing_mode = "center"
                    print("\n=== PROCESSING: CENTER CROP ===\n")
                    continue
                elif cmd == InputCommand.PROCESSING_STRETCH:
                    processing_mode = "stretch"
                    print("\n=== PROCESSING: STRETCH ===\n")
                    continue
                elif cmd == InputCommand.PROCESSING_FIT:
                    processing_mode = "fit"
                    print("\n=== PROCESSING: FIT (letterbox) ===\n")
                    continue

                # Handle effects
                elif cmd == InputCommand.TOGGLE_BW:
                    black_and_white = not black_and_white
                    mode_str = "BLACK & WHITE" if black_and_white else "COLOR"
                    print(f"\n=== {mode_str} MODE ===\n")
                    continue
                elif cmd == InputCommand.TOGGLE_MIRROR:
                    mirror_mode = not mirror_mode
                    mode_str = "ON" if mirror_mode else "OFF"
                    print(f"\n=== MIRROR: {mode_str} ===\n")
                    continue
                elif cmd == InputCommand.CYCLE_RENDER_ALGORITHM:
                    next_val = (render_algorithm.value + 1) % len(PreviewAlgorithm)
                    render_algorithm = PreviewAlgorithm(next_val)
                    print(f"\n=== RENDER ALGORITHM: {_ALGORITHM_LABELS[render_algorithm]} ===\n")
                    continue
                elif cmd == InputCommand.LED_SIZE_INCREASE:
                    if render_algorithm == PreviewAlgorithm.CIRCLES:
                        idx = (
                            LED_SIZE_STEPS.index(led_size_pct)
                            if led_size_pct in LED_SIZE_STEPS
                            else -1
                        )
                        if idx < len(LED_SIZE_STEPS) - 1:
                            led_size_pct = LED_SIZE_STEPS[idx + 1]
                        print(f"\n=== LED SIZE: {led_size_pct}% ===\n")
                    else:
                        print("\n=== LED SIZE: press 'o' to switch to Circles mode ===\n")
                    continue
                elif cmd == InputCommand.LED_SIZE_DECREASE:
                    if render_algorithm == PreviewAlgorithm.CIRCLES:
                        idx = (
                            LED_SIZE_STEPS.index(led_size_pct)
                            if led_size_pct in LED_SIZE_STEPS
                            else -1
                        )
                        if idx > 0:
                            led_size_pct = LED_SIZE_STEPS[idx - 1]
                        print(f"\n=== LED SIZE: {led_size_pct}% ===\n")
                    else:
                        print("\n=== LED SIZE: press 'o' to switch to Circles mode ===\n")
                    continue
                elif cmd == InputCommand.ZOOM_TOGGLE:
                    # Cycle: 1.0 → 0.75 → 0.5 → 0.25 → 1.0
                    if zoom_level == 1.0:
                        zoom_level = 0.75
                    elif zoom_level == 0.75:
                        zoom_level = 0.5
                    elif zoom_level == 0.5:
                        zoom_level = 0.25
                    else:
                        zoom_level = 1.0

                    zoom_pct = int(zoom_level * 100)
                    print(f"\n=== ZOOM: {zoom_pct}% ===\n")
                    continue

                # Handle actions
                elif cmd == InputCommand.TOGGLE_DISPLAY:
                    if display_enabled and transport is None:
                        # Already enabled but disconnected — reconnect without toggling to paused
                        print("\n=== RECONNECTING TO MATRIX PORTAL ===")
                        try:
                            transport = create_transport(config.transport)
                            transport.connect(args.port)
                            print(f"Connected to Matrix Portal on {transport.port}\n")
                        except DeviceNotFoundError as e:
                            print(f"Connection failed: {e}")
                            print("!!! Press 't' to try again when the portal is connected. !!!\n")
                            transport = None
                    else:
                        display_enabled = not display_enabled
                        if display_enabled:
                            print("\n=== DISPLAY: ENABLED ===")
                            if transport is None:
                                print("Attempting to reconnect to Matrix Portal...")
                                try:
                                    transport = create_transport(config.transport)
                                    transport.connect(args.port)
                                    print(f"Connected to Matrix Portal on {transport.port}\n")
                                except DeviceNotFoundError as e:
                                    print(f"Connection failed: {e}")
                                    print(
                                        "!!! Press 't' to try again when the portal is connected. !!!\n"
                                    )
                                    transport = None
                            else:
                                print()
                        else:
                            print("\n=== DISPLAY: PAUSED (by user) — press 't' to resume ===\n")
                    continue
                elif cmd == InputCommand.TOGGLE_DEBUG:
                    debug_mode = not debug_mode
                    mode_str = "ON" if debug_mode else "OFF"
                    print(f"\n=== DEBUG MODE: {mode_str} ===\n")
                    continue
                elif cmd == InputCommand.TOGGLE_PREVIEW:
                    config.ui.show_preview = not config.ui.show_preview
                    if config.ui.show_preview:
                        print("\n=== PREVIEW WINDOW: ENABLED ===\n")
                    else:
                        import cv2 as _cv2

                        _cv2.destroyAllWindows()
                        _cv2.waitKey(1)
                        print("\n=== PREVIEW WINDOW: DISABLED ===\n")
                    continue
                elif cmd == InputCommand.DEMO_TOGGLE:
                    # Reset to clean known state and start auto demo
                    orientation = "landscape"
                    processing_mode = "center"
                    black_and_white = False
                    mirror_mode = False
                    zoom_level = 1.0
                    render_algorithm = PreviewAlgorithm.GAUSSIAN_DIFFUSED
                    led_size_pct = LED_SIZE_DEFAULT
                    demo.start_auto()
                    print("\n=== DEMO MODE: AUTO (SPACE=pause, ./>=next, ,/<=prev, x=stop) ===\n")
                    continue
                elif cmd == InputCommand.DEMO_MANUAL:
                    # Reset to clean known state and start manual demo
                    orientation = "landscape"
                    processing_mode = "center"
                    black_and_white = False
                    mirror_mode = False
                    zoom_level = 1.0
                    render_algorithm = PreviewAlgorithm.GAUSSIAN_DIFFUSED
                    led_size_pct = LED_SIZE_DEFAULT
                    demo.start_manual()
                    demo_cmd = demo.next_step()
                    demo_label = demo_cmd.label
                    print("\n=== DEMO MODE: MANUAL (./>=next, ,/<=prev, x=stop) ===\n")
                    print(
                        f"--- Demo [{demo.step_position}]: {demo_cmd.description} ({demo.controls_hint}) ---"
                    )
                    cmd = demo_cmd.command
                    # Fall through to handle the first step's command
                elif cmd == InputCommand.RESET:
                    orientation = "landscape"
                    processing_mode = "center"
                    black_and_white = False
                    mirror_mode = False
                    render_algorithm = PreviewAlgorithm.GAUSSIAN_DIFFUSED
                    led_size_pct = LED_SIZE_DEFAULT
                    debug_mode = False
                    zoom_level = 1.0
                    display_enabled = True
                    print("\n=== RESET TO DEFAULTS ===")
                    print(
                        "Orientation=landscape, Processing=center, Color, Mirror=OFF, "
                        "Algorithm=diffused panel emulation, Size=100%, Debug=OFF, Zoom=100%, Display=ON\n"
                    )
                    continue
                elif cmd == InputCommand.HELP:
                    print_help(
                        orientation,
                        processing_mode,
                        black_and_white,
                        debug_mode,
                        zoom_level,
                        config.ui.show_preview,
                        mirror_mode,
                        _ALGORITHM_LABELS[render_algorithm],
                        led_size_pct,
                    )
                    continue
                elif cmd == InputCommand.QUIT:
                    print("\n=== QUIT REQUESTED ===\n")
                    break
                elif cmd == InputCommand.SNAPSHOT:
                    if not save_enabled:
                        print("  Snapshot saving disabled (--no-save)")
                    elif not display_enabled and last_sent_frame is not None:
                        # Paused: save the frozen frame on the device — no countdown
                        print("  Saving paused frame...")
                        frame_bytes_save = convert_to_rgb565(last_sent_frame)
                        snapshot_manager.save(
                            last_sent_frame, frame_bytes_save, orientation, debug_mode=debug_mode
                        )
                        print("  Saved.")
                    else:
                        run_snapshot_sequence(
                            camera,
                            transport,
                            config,
                            snapshot_manager,
                            keyboard,
                            black_and_white,
                            orientation,
                            processing_mode,
                            zoom_level,
                            debug_mode,
                            mirror_mode,
                            render_algorithm,
                            led_size_pct,
                        )
                    keyboard.clear_buffer()
                    continue
                elif cmd == InputCommand.AVATAR:
                    # Run avatar capture mode
                    avatar_manager = AvatarCaptureManager()
                    avatar_manager.run_capture_session(
                        camera=camera,
                        transport=transport,
                        config=config,
                        orientation=orientation,
                        processing_mode=processing_mode,
                        zoom_level=zoom_level,
                        resize_fn=resize_frame,
                        convert_fn=convert_to_rgb565,
                    )
                    keyboard.clear_buffer()
                    continue

                # Capture frame
                try:
                    original_frame = camera.capture()  # Full resolution, pre-zoom
                except CameraCaptureFailed:
                    time.sleep(0.1)
                    continue

                # Apply zoom (frame is the working copy; original_frame stays full-res for preview)
                frame = original_frame
                if zoom_level < 1.0:
                    frame = apply_zoom_crop(frame, zoom_level)

                # Process frame
                small_frame = resize_frame(
                    frame, config.matrix, config.processing, orientation, processing_mode
                )
                if mirror_mode:
                    small_frame = apply_mirror(small_frame, orientation)
                if black_and_white:
                    small_frame = apply_grayscale(small_frame)

                # Save frame before brightness limiting — show_preview applies it internally
                preview_frame = small_frame

                # In demo mode, draw current step label in red on device frame and preview
                if demo.is_active and demo_label:
                    small_frame = draw_text_overlay(
                        small_frame,
                        demo_label,
                        (2, 30),
                        color=(0, 0, 255),
                        font_scale=0.225,
                        thickness=1,
                    )
                    preview_frame = small_frame

                # Apply brightness limiting for USB power safety
                if config.processing.max_brightness < 255:
                    small_frame = apply_brightness_limit(
                        small_frame, config.processing.max_brightness
                    )

                # Debug save
                if config.debug_save_frames:
                    snapshot_manager.save_debug_frame(small_frame)

                # Convert and send
                frame_bytes = convert_to_rgb565(small_frame)
                bytes_sent = 0

                # Determine display status and send if enabled
                if not display_enabled:
                    display_status = "PAUSED (user)"
                elif transport is None:
                    display_status = "PAUSED (no device)"
                else:
                    try:
                        bytes_sent = transport.send_frame(frame_bytes)
                        display_status = "ACTIVE"
                        last_sent_frame = small_frame  # Cache for pause-mode snapshot
                    except Exception as e:
                        transport = None  # Mark as disconnected so 't' can reconnect
                        display_status = "PAUSED (disconnected)"
                        print(f"Display disconnected: {e}")
                        print(
                            "\n!!! Matrix Portal disconnected — plug in and press 't' to reconnect. !!!\n"
                        )

                # Frame counting and stats
                frame_count += 1
                if frame_count == 1 and display_status == "ACTIVE":
                    print(f"First frame sent: {bytes_sent} bytes")

                if debug_mode and frame_count % 10 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    bw_status = " [B&W]" if black_and_white else ""
                    mode_status = f" [{orientation}/{processing_mode}]"
                    zoom_status = f" [zoom={int(zoom_level * 100)}%]" if zoom_level < 1.0 else ""
                    display_info = (
                        f", Display: {display_status}" if display_status != "ACTIVE" else ""
                    )
                    print(
                        f"Frames: {frame_count}, FPS: {fps:.1f}, "
                        f"Bytes: {bytes_sent}/{len(frame_bytes)}{bw_status}{mode_status}{zoom_status}{display_info}"
                    )

                # Preview window
                if config.ui.show_preview:
                    show_preview(
                        original_frame,
                        preview_frame,
                        config.matrix,
                        orientation,
                        processing_mode,
                        zoom_level,
                        render_algorithm,
                        led_size_pct,
                        config.processing.max_brightness,
                        demo_label if demo.is_active else "",
                    )

                # Frame rate limiting
                if config.ui.enable_frame_limiting:
                    elapsed = time.time() - loop_start
                    sleep_time = max(0, frame_time - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                # Check frame limit
                if args.frames > 0 and frame_count >= args.frames:
                    print(f"Reached target of {args.frames} frames. Stopping.")
                    break

    except KeyboardInterrupt:
        print("\nStopping...")
    except LEDPortalError as e:
        print(f"Error: {e}")
        return 1
    finally:
        # Cleanup
        if camera is not None:
            camera.close()
        if transport is not None:
            transport.disconnect()
        if console_serial is not None:
            try:
                console_serial.close()
            except Exception:
                pass
        if config.ui.show_preview:
            import cv2 as _cv2

            _cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
