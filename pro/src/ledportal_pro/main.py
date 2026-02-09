#!/usr/bin/env python3
"""Main entry point for LED Portal Pro."""

import argparse
import sys
import time
from pathlib import Path

from .capture import create_camera
from .config import AppConfig, load_config
from .exceptions import CameraCaptureFailed, DeviceNotFoundError, LEDPortalError
from .processing import apply_grayscale, convert_to_rgb565, create_test_pattern, resize_frame
from .transport import create_transport
from .ui import (
    AvatarCaptureManager,
    InputCommand,
    KeyboardHandler,
    SnapshotManager,
    draw_countdown_overlay,
    print_help,
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
        help="Run without connecting to Matrix Portal (test mode)",
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

    Returns:
        True if snapshot completed, False if aborted.
    """
    print("\n=== SNAPSHOT MODE (SPACE or r to cancel) ===")
    print(f"Countdown: 3... 2... 1... ({config.ui.countdown_duration}s each)")
    speak("Get ready")

    from .capture.base import CameraBase

    camera_typed = camera if isinstance(camera, CameraBase) else None
    if camera_typed is None:
        print("Error: Invalid camera type")
        return False

    # Countdown with overlay
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
                frame = camera_typed.capture()
            except CameraCaptureFailed:
                continue

            small_frame = resize_frame(
                frame, config.matrix, config.processing, orientation, processing_mode
            )
            if black_and_white:
                small_frame = apply_grayscale(small_frame)

            overlay_frame = draw_countdown_overlay(small_frame, countdown, config.matrix)
            frame_bytes = convert_to_rgb565(overlay_frame)

            if transport is not None:
                from .transport.base import TransportBase

                if isinstance(transport, TransportBase):
                    try:
                        transport.send_frame(frame_bytes)
                    except Exception:
                        pass

            time.sleep(0.01)

    # Capture final frame
    print("SNAP!")
    speak("Got it")
    try:
        frame = camera_typed.capture()
        small_frame = resize_frame(
            frame, config.matrix, config.processing, orientation, processing_mode
        )
        if black_and_white:
            small_frame = apply_grayscale(small_frame)
        frame_bytes = convert_to_rgb565(small_frame)

        # Save snapshot
        image_path, rgb565_path = snapshot_manager.save(small_frame, frame_bytes)
        print(f"\n{'=' * 60}")
        print("SNAPSHOT SAVED:")
        print(f"  Color BMP: {image_path}")
        if rgb565_path:
            print(f"  RGB565 data: {rgb565_path}")
        print(f"{'=' * 60}\n")

        # Send to display
        if transport is not None:
            from .transport.base import TransportBase

            if isinstance(transport, TransportBase):
                try:
                    transport.send_frame(frame_bytes)
                except Exception:
                    pass

        # Pause (can be aborted)
        print("Pausing for 5 seconds (SPACE or r to resume)...")
        print("Resuming in: ", end="", flush=True)
        for i in range(int(config.ui.snapshot_pause_duration), 0, -1):
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
    if args.mode is not None:
        config.processing.display_mode = args.mode

    # Print startup info
    print("LED Portal Pro v1.0.0")
    print(f"Matrix: {config.matrix.width}x{config.matrix.height}")
    print(f"Target FPS: {config.target_fps}")
    print(f"Frame size: {config.frame_size_bytes} bytes (RGB565)")
    if args.frames > 0:
        print(f"Will capture {args.frames} frames and exit")
    print()

    # Initialize state
    camera = None
    transport = None
    black_and_white = args.bw
    display_mode = config.processing.display_mode
    debug_mode = config.ui.debug_mode

    try:
        # Setup camera
        camera = create_camera(config.camera)
        camera.open()
        print(f"Camera ready: {camera.get_camera_type()}")

        # Setup transport (optional)
        if not args.no_display:
            transport = create_transport(config.transport)
            try:
                transport.connect(args.port)
                print(f"Connected to Matrix Portal on {transport.port}")

                # Send test patterns to verify connection
                test_pattern = create_test_pattern(config.matrix)
                for i in range(5):
                    bytes_sent = transport.send_frame(test_pattern)
                    print(f"Test pattern {i + 1} sent: {bytes_sent} bytes")
                    time.sleep(0.1)
                print("Verification frames sent.")
            except DeviceNotFoundError as e:
                print(f"Warning: {e}")
                print("Running in test mode (no display)")
                transport = None

        # Setup UI components
        snapshot_manager = SnapshotManager()

        print()
        print("Starting capture loop...")
        print()
        print("Commands (single keypress):")
        print("  Display: l=landscape  p=portrait")
        print("  Effects: b=B&W  c=color")
        print("  Actions: SPACE=snapshot  v=avatar  d=debug  r=reset  h=help  q=quit")
        print()
        bw_str = "B&W" if black_and_white else "Color"
        debug_str = "ON" if debug_mode else "OFF"
        print(f"Current: Mode={display_mode}, {bw_str}, Debug={debug_str}")
        print()
        print("Attempting first frame capture...")

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

                # Handle display mode changes
                if cmd == InputCommand.MODE_LANDSCAPE:
                    display_mode = "landscape"
                    print("\n=== DISPLAY MODE: LANDSCAPE (center crop) ===\n")
                    continue
                elif cmd == InputCommand.MODE_PORTRAIT:
                    display_mode = "portrait"
                    print("\n=== DISPLAY MODE: PORTRAIT ===\n")
                    continue

                # Handle effects
                elif cmd == InputCommand.BLACK_WHITE:
                    black_and_white = True
                    print("\n=== BLACK & WHITE MODE ===\n")
                    continue
                elif cmd == InputCommand.COLOR:
                    black_and_white = False
                    print("\n=== COLOR MODE (normal) ===\n")
                    continue

                # Handle actions
                elif cmd == InputCommand.TOGGLE_DEBUG:
                    debug_mode = not debug_mode
                    mode_str = "ON" if debug_mode else "OFF"
                    print(f"\n=== DEBUG MODE: {mode_str} ===\n")
                    continue
                elif cmd == InputCommand.RESET:
                    display_mode = "landscape"
                    black_and_white = False
                    debug_mode = True
                    print("\n=== RESET TO DEFAULTS ===")
                    print("Mode=landscape, Color, Debug=ON\n")
                    continue
                elif cmd == InputCommand.HELP:
                    print_help(display_mode, black_and_white, debug_mode)
                    continue
                elif cmd == InputCommand.QUIT:
                    print("\n=== QUIT REQUESTED ===\n")
                    break
                elif cmd == InputCommand.SNAPSHOT:
                    run_snapshot_sequence(
                        camera,
                        transport,
                        config,
                        snapshot_manager,
                        keyboard,
                        black_and_white,
                        display_mode,
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
                        display_mode=display_mode,
                        resize_fn=resize_frame,
                        convert_fn=convert_to_rgb565,
                    )
                    keyboard.clear_buffer()
                    continue

                # Capture frame
                try:
                    frame = camera.capture()
                except CameraCaptureFailed as e:
                    print(f"Capture failed: {e}")
                    time.sleep(0.1)
                    continue

                # Process frame
                small_frame = resize_frame(
                    frame, config.matrix, config.processing, orientation, processing_mode
                )
                if black_and_white:
                    small_frame = apply_grayscale(small_frame)

                # Debug save
                if config.debug_save_frames:
                    snapshot_manager.save_debug_frame(small_frame)

                # Convert and send
                frame_bytes = convert_to_rgb565(small_frame)
                bytes_sent = 0
                if transport is not None:
                    try:
                        bytes_sent = transport.send_frame(frame_bytes)
                    except Exception as e:
                        print(f"Send failed: {e}")

                # Frame counting and stats
                frame_count += 1
                if frame_count == 1:
                    print(f"First frame sent: {bytes_sent} bytes")

                if debug_mode and frame_count % 10 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    bw_status = " [B&W]" if black_and_white else ""
                    mode_status = f" [{display_mode.upper()}]" if display_mode != "landscape" else ""
                    print(
                        f"Frames: {frame_count}, FPS: {fps:.1f}, "
                        f"Bytes: {bytes_sent}/{len(frame_bytes)}{bw_status}{mode_status}"
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
