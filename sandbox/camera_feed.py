#!/usr/bin/env python3
"""
Camera feed capture and conversion for LED Matrix display.
Cross-platform: works on macOS (webcam) and Raspberry Pi (Pi Camera or USB webcam).
Captures frames, resizes to 64x32, and converts to RGB565 format.
"""

import time
import numpy as np
import cv2
import serial
import serial.tools.list_ports
import argparse
import sys
import select
import tty
import termios
import subprocess
import platform
import os
import json
from datetime import datetime
from config import MATRIX_WIDTH, MATRIX_HEIGHT, CAMERA_WIDTH, CAMERA_HEIGHT, TARGET_FPS

# Protocol constant
FRAME_HEADER = b'IMG1'

# Snapshot countdown duration (seconds per number)
COUNTDOWN_DURATION = 0.5  # How long to show each number (3, 2, 1)

# Frame rate limiting (0 = disabled, sends as fast as possible)
ENABLE_FRAME_LIMITING = 0  # Set to 1 to limit to TARGET_FPS

# Black and white mode (toggled with 'b' key)
black_and_white_mode = False

# Display mode: 'landscape' (2:1 crop), 'portrait' (1:2 crop, rotated), 'squish' (no crop)
display_mode = 'landscape'

# Debug mode (toggled with 'd' key) - shows frame rate and other stats
debug_mode = True

# Avatar capture pose list: (angle, expression, voice_prompt)
AVATAR_POSES = [
    # Front facing
    ("front", "neutral", "Front facing, neutral expression"),
    ("front", "smile", "Front facing, give me a smile"),
    ("front", "smile_open", "Front facing, smile with teeth"),
    ("front", "eyebrows_up", "Front facing, raise your eyebrows"),
    ("front", "eyes_closed", "Front facing, close your eyes"),
    # Left 45 degrees
    ("left", "neutral", "Turn left 45 degrees, neutral"),
    ("left", "smile", "Stay left, give me a smile"),
    ("left", "eyebrows_up", "Stay left, raise your eyebrows"),
    # Right 45 degrees
    ("right", "neutral", "Turn right 45 degrees, neutral"),
    ("right", "smile", "Stay right, give me a smile"),
    ("right", "eyebrows_up", "Stay right, raise your eyebrows"),
    # Up tilt
    ("up", "neutral", "Tilt chin up slightly, neutral"),
    ("up", "smile", "Stay tilted up, smile"),
    # Down tilt
    ("down", "neutral", "Tilt chin down slightly, neutral"),
    ("down", "smile", "Stay tilted down, smile"),
    # Mouth shapes for animation
    ("front", "mouth_o", "Front facing, make an O shape with your mouth"),
    ("front", "mouth_ee", "Front facing, say cheese, hold the ee sound"),
    ("front", "mouth_closed", "Front facing, lips together"),
]


def speak_prompt(text, voice=None):
    """Speak a prompt using system text-to-speech.

    Uses robotic/stylized voices that match the pixel art aesthetic.
    Cross-platform: macOS (say), Linux (espeak-ng), Windows (pyttsx3).
    """
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            # Zarvox is a classic robot voice, Trinoids is alien-like
            voice = voice or "Zarvox"
            subprocess.run(["say", "-v", voice, text], check=False)

        elif system == "Linux":
            # espeak-ng with robot-style settings
            # -v en+m3 = male voice variant 3 (robotic)
            # -s 130 = speed (words per minute)
            # -p 30 = pitch (0-99, lower = more robotic)
            subprocess.run(
                ["espeak-ng", "-v", "en+m3", "-s", "130", "-p", "30", text],
                check=False,
                stderr=subprocess.DEVNULL
            )

        else:  # Windows
            # Use pyttsx3 if available, otherwise skip
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 130)
                engine.say(text)
                engine.runAndWait()
            except ImportError:
                print(f"  (Voice unavailable - install pyttsx3)")

    except FileNotFoundError:
        # TTS not installed, just print
        pass
    except Exception:
        # Any other error, continue without voice
        pass


def avatar_capture_mode(camera, camera_type, usb_serial, display_mode):
    """Guided avatar capture session with voice prompts.

    Walks through each pose, speaks the prompt, and saves captures
    with structured naming for later avatar generation.

    Args:
        camera: Camera object
        camera_type: "picamera" or "opencv"
        usb_serial: Serial connection to Matrix Portal (or None)
        display_mode: Current display mode

    Returns:
        List of captured file paths
    """
    # Create avatar output directory
    session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    avatar_dir = f"avatar_{session_time}"
    os.makedirs(avatar_dir, exist_ok=True)

    print("\n" + "=" * 60)
    print("   AVATAR CAPTURE MODE")
    print("=" * 60)
    print(f"\nCapturing {len(AVATAR_POSES)} poses to: {avatar_dir}/")
    print("\nControls:")
    print("  SPACE = Capture this pose")
    print("  S     = Skip this pose")
    print("  R     = Repeat voice prompt")
    print("  Q     = Quit avatar mode")
    print("\nTip: Use 'p' before starting for portrait mode (faces fit better)")
    print("=" * 60)

    speak_prompt("Avatar capture mode. Get ready.")
    time.sleep(1)

    captured = []
    skipped = []

    for i, (angle, expression, prompt) in enumerate(AVATAR_POSES):
        pose_num = i + 1
        total = len(AVATAR_POSES)
        filename = f"avatar_{angle}_{expression}.bmp"
        filepath = os.path.join(avatar_dir, filename)

        print(f"\n--- Pose {pose_num}/{total}: {angle} - {expression} ---")
        print(f"Prompt: {prompt}")

        # Speak the prompt
        speak_prompt(prompt)

        # Capture loop for this pose
        waiting = True
        while waiting:
            # Capture and display frame continuously
            frame = capture_frame(camera, camera_type)
            if frame is not None:
                small_frame = resize_frame(frame, display_mode)
                frame_bytes = convert_to_rgb565(small_frame)
                send_frame_usb(usb_serial, frame_bytes)

            # Check for input
            if select.select([sys.stdin], [], [], 0.01)[0]:
                key = sys.stdin.read(1).lower()

                if key == ' ':
                    # Capture this pose
                    if frame is not None:
                        cv2.imwrite(filepath, small_frame)
                        # Also save RGB565 for direct LED use
                        rgb565_path = filepath.replace('.bmp', '_rgb565.bin')
                        with open(rgb565_path, 'wb') as f:
                            f.write(frame_bytes)

                        captured.append({
                            "pose": pose_num,
                            "angle": angle,
                            "expression": expression,
                            "file": filename,
                            "rgb565_file": os.path.basename(rgb565_path)
                        })
                        print(f"  ✓ Captured: {filename}")
                        speak_prompt("Got it")
                        waiting = False
                    else:
                        print("  ✗ Capture failed, try again")
                        speak_prompt("Capture failed, try again")

                elif key == 's':
                    # Skip this pose
                    skipped.append({"pose": pose_num, "angle": angle, "expression": expression})
                    print(f"  → Skipped")
                    speak_prompt("Skipped")
                    waiting = False

                elif key == 'r':
                    # Repeat prompt
                    speak_prompt(prompt)

                elif key == 'q':
                    # Quit avatar mode
                    print("\n  Avatar capture cancelled.")
                    speak_prompt("Avatar capture cancelled")
                    # Save partial manifest
                    _save_avatar_manifest(avatar_dir, captured, skipped, session_time)
                    return captured

    # Session complete
    print("\n" + "=" * 60)
    print("   AVATAR CAPTURE COMPLETE")
    print("=" * 60)
    print(f"\nCaptured: {len(captured)} poses")
    print(f"Skipped:  {len(skipped)} poses")
    print(f"Location: {avatar_dir}/")

    speak_prompt(f"Avatar capture complete. {len(captured)} poses saved.")

    # Save manifest
    _save_avatar_manifest(avatar_dir, captured, skipped, session_time)

    return captured


def _save_avatar_manifest(avatar_dir, captured, skipped, session_time):
    """Save a JSON manifest of the avatar capture session."""
    manifest = {
        "session": session_time,
        "total_poses": len(AVATAR_POSES),
        "captured_count": len(captured),
        "skipped_count": len(skipped),
        "captured": captured,
        "skipped": skipped,
        "matrix_size": {"width": MATRIX_WIDTH, "height": MATRIX_HEIGHT}
    }

    manifest_path = os.path.join(avatar_dir, "manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest saved: {manifest_path}")


def setup_camera(camera_index=0):
    """Initialize camera: tries Pi Camera first, then USB webcam.

    Returns:
        tuple: (camera_object, camera_type)
        camera_type is either "picamera" or "opencv"
    """
    # Try Pi Camera first (Raspberry Pi only)
    try:
        from picamera2 import Picamera2
        print("Trying Pi Camera...")
        picam = Picamera2()
        config = picam.create_preview_configuration(
            main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT)}
        )
        picam.configure(config)
        picam.start()
        print("Pi Camera initialized successfully")
        return picam, "picamera"
    except ImportError:
        print("picamera2 not available (not on Raspberry Pi)")
    except Exception as e:
        print(f"Pi Camera failed: {e}")
        print("Falling back to USB webcam...")

    # Fall back to USB webcam (OpenCV)
    print(f"Initializing webcam (camera {camera_index})...")
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera {camera_index}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    print("USB webcam initialized successfully")
    return cap, "opencv"


def capture_frame(camera, camera_type):
    """Capture a single frame from camera.

    Args:
        camera: The camera object (Picamera2 or cv2.VideoCapture)
        camera_type: Either "picamera" or "opencv"

    Returns:
        Frame as BGR numpy array, or None if capture failed.
    """
    if camera_type == "picamera":
        # Pi Camera returns RGB, convert to BGR for consistency
        frame = camera.capture_array()
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    else:
        # USB webcam (OpenCV) returns BGR directly
        ret, frame = camera.read()
        if not ret:
            return None
        return frame


def resize_frame(frame, mode='landscape'):
    """Crop and resize frame to matrix dimensions.

    Modes:
    - 'landscape': Crops to 2:1 aspect ratio from center, for horizontal matrix
    - 'portrait': Crops to 1:2 aspect ratio from center, rotates 90° for vertical matrix
    - 'squish': No cropping, stretches entire frame to fit (may distort)
    - 'letterbox': No cropping, maintains aspect ratio, black bars fill empty space
    """
    h, w = frame.shape[:2]

    if mode == 'letterbox':
        # Maintain aspect ratio, center on black background
        # Calculate scale to fit within matrix dimensions
        scale_w = MATRIX_WIDTH / w
        scale_h = MATRIX_HEIGHT / h
        scale = min(scale_w, scale_h)  # Use smaller scale to fit entirely

        # Calculate new dimensions
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Resize proportionally
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Create black canvas
        canvas = np.zeros((MATRIX_HEIGHT, MATRIX_WIDTH, 3), dtype=np.uint8)

        # Calculate centering offsets
        x_offset = (MATRIX_WIDTH - new_w) // 2
        y_offset = (MATRIX_HEIGHT - new_h) // 2

        # Place resized image on canvas
        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return canvas

    elif mode == 'squish':
        # No cropping - stretch entire frame to fit matrix
        return cv2.resize(frame, (MATRIX_WIDTH, MATRIX_HEIGHT), interpolation=cv2.INTER_LINEAR)

    elif mode == 'portrait':
        # Crop to 1:2 aspect ratio (tall and narrow) from center
        # Keep full height, crop width to half of height
        target_w = h // 2
        if target_w > w:
            target_w = w

        # Center crop horizontally
        start_x = (w - target_w) // 2
        cropped = frame[0:h, start_x:start_x + target_w]

        # Resize to swapped dimensions (32x64), then rotate 90° clockwise
        resized = cv2.resize(cropped, (MATRIX_HEIGHT, MATRIX_WIDTH), interpolation=cv2.INTER_LINEAR)

        # Rotate 90° clockwise for portrait orientation
        rotated = cv2.rotate(resized, cv2.ROTATE_90_CLOCKWISE)
        return rotated

    else:  # 'landscape' (default)
        # Crop to 2:1 aspect ratio from center
        # Keep full width, crop height to half of width
        target_h = w // 2
        if target_h > h:
            target_h = h

        # Center crop vertically
        start_y = (h - target_h) // 2
        cropped = frame[start_y:start_y + target_h, 0:w]

        # Resize to matrix dimensions
        return cv2.resize(cropped, (MATRIX_WIDTH, MATRIX_HEIGHT), interpolation=cv2.INTER_LINEAR)


def convert_to_rgb565(frame):
    """Convert BGR frame to RGB565 format (16-bit color).

    Returns bytes array ready for USB transfer.
    Each pixel is 2 bytes: RRRRR GGGGGG BBBBB
    """
    # Convert BGR to RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Extract color channels
    r = (rgb[:, :, 0] >> 3).astype(np.uint16)  # 5 bits
    g = (rgb[:, :, 1] >> 2).astype(np.uint16)  # 6 bits
    b = (rgb[:, :, 2] >> 3).astype(np.uint16)  # 5 bits

    # Pack into RGB565 format
    rgb565 = (r << 11) | (g << 5) | b

    # Convert to bytes (little-endian)
    return rgb565.astype('<u2').tobytes()


def find_matrix_portal():
    """Find the Matrix Portal M4 USB CDC serial port.

    Returns serial port path or None if not found.
    """
    ports = serial.tools.list_ports.comports()
    matrix_ports = []

    # Collect all Matrix Portal ports
    for port in ports:
        if "CircuitPython" in port.description or "Matrix Portal" in port.description:
            matrix_ports.append(port)

    if not matrix_ports:
        return None

    # If we have multiple ports, use the one with higher number (typically the data port)
    # Otherwise use the only one available
    if len(matrix_ports) > 1:
        matrix_ports.sort(key=lambda p: p.device)
        return matrix_ports[-1].device  # Last one (highest number)
    else:
        return matrix_ports[0].device


def setup_usb_serial(requested_baud=2000000):
    """Connect to Matrix Portal M4 via USB serial.

    Returns serial connection or None if failed.
    """
    port = find_matrix_portal()
    if port is None:
        print("Matrix Portal M4 not found. Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device}: {p.description}")
        return None

    print(f"Connecting to Matrix Portal M4 on {port}")
    print(f"Requested baud rate: {requested_baud:,} bps")
    try:
        ser = serial.Serial(
            port,
            baudrate=requested_baud,
            timeout=0.1,
            write_timeout=0.5,
            rtscts=False,  # Disable hardware flow control
            dsrdtr=False   # Disable hardware flow control
        )
        time.sleep(0.5)  # Give the connection time to stabilize

        # Display actual baud rate (may differ from requested)
        actual_baud = ser.baudrate
        print(f"Actual baud rate:    {actual_baud:,} bps", end="")
        if actual_baud != requested_baud:
            print(f" (WARNING: differs from requested!)")
        else:
            print(" ✓")

        return ser
    except Exception as e:
        print(f"Failed to connect: {e}")
        return None


def send_frame_usb(serial_port, frame_bytes):
    """Send frame data via USB serial to Matrix Portal M4."""
    if serial_port and serial_port.is_open:
        # Send header then frame data
        serial_port.write(FRAME_HEADER)
        bytes_written = serial_port.write(frame_bytes)
        serial_port.flush()  # Ensure data is sent immediately
        return bytes_written
    return 0


def create_test_pattern():
    """Create a simple test pattern frame in RGB565 format.

    Creates a colorful gradient pattern to verify USB communication.
    """
    frame = np.zeros((MATRIX_HEIGHT, MATRIX_WIDTH, 3), dtype=np.uint8)

    # Create a gradient pattern
    for y in range(MATRIX_HEIGHT):
        for x in range(MATRIX_WIDTH):
            # Red gradient horizontally, Green gradient vertically
            frame[y, x, 0] = int((x / MATRIX_WIDTH) * 255)  # Red
            frame[y, x, 1] = int((y / MATRIX_HEIGHT) * 255)  # Green
            frame[y, x, 2] = 128  # Blue constant

    return convert_to_rgb565(frame)


def check_keyboard_input():
    """Check for keyboard input without blocking.

    Returns a single character or None if no input.
    Requires terminal to be in cbreak mode (set in main()).
    """
    if select.select([sys.stdin], [], [], 0)[0]:
        char = sys.stdin.read(1).lower()
        return char
    return None


def apply_black_and_white(frame):
    """Convert a BGR frame to black and white (grayscale).

    Returns a BGR frame where all channels have the same grayscale value.
    This keeps the frame in 3-channel format for compatibility with RGB565 conversion.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Convert back to BGR (3 channels) so it works with our existing pipeline
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def save_snapshot(frame, frame_bytes):
    """Save the current frame as a timestamped bitmap file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save the full-color resized frame
    color_filename = f"snapshot_{timestamp}.bmp"
    cv2.imwrite(color_filename, frame)

    # Also save the RGB565 version for debugging
    rgb565_filename = f"snapshot_{timestamp}_rgb565.bin"
    with open(rgb565_filename, 'wb') as f:
        f.write(frame_bytes)

    print(f"\n{'='*60}")
    print(f"SNAPSHOT SAVED:")
    print(f"  Color BMP: {color_filename}")
    print(f"  RGB565 data: {rgb565_filename}")
    print(f"{'='*60}\n")

    return color_filename

def main():
    """Main loop: capture, process, and send frames."""
    global black_and_white_mode, display_mode, debug_mode

    # Save terminal settings and set to cbreak mode for single-keypress input
    # NOTE: This only works on Mac/Linux. Windows support planned for future.
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    parser = argparse.ArgumentParser(description="Camera feed for LED matrix.")
    parser.add_argument("--frames", type=int, default=0, help="Number of frames to capture (0 for infinite)")
    args = parser.parse_args()

    print(f"Starting camera feed for {MATRIX_WIDTH}x{MATRIX_HEIGHT} LED matrix")
    if args.frames > 0:
        print(f"Will capture {args.frames} frames and then exit.")
    
    print(f"Target FPS: {TARGET_FPS}")
    print(f"Frame size: {MATRIX_WIDTH * MATRIX_HEIGHT * 2} bytes (RGB565)")

    camera, camera_type = setup_camera()
    print(f"Camera ready ({camera_type})")

    # Connect to Matrix Portal M4
    usb_serial = setup_usb_serial()
    
    # Always create test pattern for verification
    test_pattern = create_test_pattern()
    if usb_serial is None:
        print("Warning: Matrix Portal M4 not connected. Running in test mode.")
    else:
        print("Connected to Matrix Portal M4")

        # Send test pattern to verify connection
        # Send multiple times to verify connection
        for i in range(5):
            bytes_sent = send_frame_usb(usb_serial, test_pattern)
            print(f"Test pattern {i+1} sent: {bytes_sent} bytes")
            time.sleep(0.1)

        print("Verification frames sent.")

    frame_count = 0
    start_time = time.time()

    print("Starting capture loop...")
    print("")
    print("Commands (single keypress):")
    print("  Display: c=crop  s=squish  l=letterbox  p=portrait")
    print("  Effects: b=B&W  n=normal(color)")
    print("  Actions: SPACE=snapshot  v=avatar  d=debug  r=reset  h=help  q=quit")
    print("")
    bw_str = "B&W" if black_and_white_mode else "Color"
    debug_str = "ON" if debug_mode else "OFF"
    print(f"Current: Mode={display_mode}, {bw_str}, Debug={debug_str}")
    print("")
    print("Attempting first frame capture...")

    # Set terminal to cbreak mode for single-keypress input
    tty.setcbreak(sys.stdin.fileno())

    try:
        while True:
            loop_start = time.time()

            # Check for keyboard input
            key_input = check_keyboard_input()

            # Handle 'b' key - black and white mode ON
            if key_input == 'b':
                black_and_white_mode = True
                print(f"\n=== BLACK & WHITE MODE ===\n")
                continue

            # Handle 'n' key - normal color mode
            if key_input == 'n':
                black_and_white_mode = False
                print(f"\n=== COLOR MODE (normal) ===\n")
                continue

            # Handle 'p' key - portrait mode
            if key_input == 'p':
                display_mode = 'portrait'
                print(f"\n=== DISPLAY MODE: PORTRAIT ===\n")
                continue

            # Handle 's' key - squish mode
            if key_input == 's':
                display_mode = 'squish'
                print(f"\n=== DISPLAY MODE: SQUISH ===\n")
                continue

            # Handle 'l' key - letterbox mode
            if key_input == 'l':
                display_mode = 'letterbox'
                print(f"\n=== DISPLAY MODE: LETTERBOX ===\n")
                continue

            # Handle 'd' key - toggle debug mode
            if key_input == 'd':
                debug_mode = not debug_mode
                mode_str = "ON" if debug_mode else "OFF"
                print(f"\n=== DEBUG MODE: {mode_str} ===\n")
                continue

            # Handle 'q' key - quit
            if key_input == 'q':
                print("\n=== QUIT REQUESTED ===\n")
                break

            # Handle 'r' key - reset to defaults
            if key_input == 'r':
                display_mode = 'landscape'
                black_and_white_mode = False
                debug_mode = True
                print("\n=== RESET TO DEFAULTS ===")
                print("Mode=landscape, Color, Debug=ON\n")
                continue

            # Handle 'c' key - landscape (crop) mode
            if key_input == 'c':
                display_mode = 'landscape'
                print(f"\n=== DISPLAY MODE: LANDSCAPE (center crop) ===\n")
                continue

            # Handle 'h' key - show help
            if key_input == 'h':
                print("")
                print("=" * 50)
                print("Commands (single keypress):")
                print("  Display: c=crop  s=squish  l=letterbox  p=portrait")
                print("  Effects: b=B&W  n=normal(color)")
                print("  Actions: SPACE=snapshot  v=avatar  d=debug  r=reset  h=help  q=quit")
                print("")
                bw_str = "B&W" if black_and_white_mode else "Color"
                debug_str = "ON" if debug_mode else "OFF"
                print(f"Current: Mode={display_mode}, {bw_str}, Debug={debug_str}")
                print("=" * 50)
                print("")
                continue

            # Handle 'v' key - avatar capture mode
            if key_input == 'v':
                avatar_capture_mode(camera, camera_type, usb_serial, display_mode)
                # Clear any buffered input after avatar mode
                while select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)
                continue

            # Handle Space key - snapshot request
            if key_input == ' ':
                print("\n=== SNAPSHOT MODE (SPACE or r to cancel) ===")
                print(f"Countdown: 3... 2... 1... ({COUNTDOWN_DURATION}s each)")

                # 3-2-1 countdown with visual overlay
                # Each number shows for COUNTDOWN_DURATION seconds
                snapshot_aborted = False
                for countdown in [3, 2, 1]:
                    if snapshot_aborted:
                        break
                    print(f"  Showing: {countdown}", flush=True)
                    countdown_start = time.time()

                    # Keep showing this number for the configured duration
                    while time.time() - countdown_start < COUNTDOWN_DURATION:
                        # Check for abort (space or r)
                        abort_key = check_keyboard_input()
                        if abort_key in (' ', 'r'):
                            print("\n=== SNAPSHOT CANCELLED ===\n")
                            snapshot_aborted = True
                            break

                        frame = capture_frame(camera, camera_type)
                        if frame is None:
                            print("Failed to capture countdown frame")
                            continue

                        # Resize frame
                        small_frame = resize_frame(frame, display_mode)

                        # Apply black and white filter if enabled
                        if black_and_white_mode:
                            small_frame = apply_black_and_white(small_frame)

                        # Add countdown text overlay on lower left
                        overlay_frame = small_frame.copy()
                        cv2.putText(
                            overlay_frame,
                            str(countdown),
                            (2, MATRIX_HEIGHT - 4),  # Lower left position
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,  # Font scale
                            (0, 0, 255),  # Red color (BGR format)
                            2,  # Thickness
                            cv2.LINE_AA
                        )

                        # Convert and send the overlay frame to display
                        frame_bytes = convert_to_rgb565(overlay_frame)
                        send_frame_usb(usb_serial, frame_bytes)

                        # Small sleep to avoid hammering the camera
                        time.sleep(0.01)

                if snapshot_aborted:
                    # Clear any buffered input and continue
                    while select.select([sys.stdin], [], [], 0)[0]:
                        sys.stdin.read(1)
                    continue

                # Capture the final clean frame (no overlay)
                print("SNAP!")
                frame = capture_frame(camera, camera_type)
                if frame is not None:
                    small_frame = resize_frame(frame, display_mode)
                    # Apply black and white filter if enabled
                    if black_and_white_mode:
                        small_frame = apply_black_and_white(small_frame)
                    frame_bytes = convert_to_rgb565(small_frame)
                    save_snapshot(small_frame, frame_bytes)

                    # Send the clean frame to display
                    send_frame_usb(usb_serial, frame_bytes)

                    # Pause for 5 seconds (can be aborted with space or r)
                    print("Pausing for 5 seconds (SPACE or r to resume)...")
                    print("Resuming in: ", end="", flush=True)
                    for i in range(5, 0, -1):
                        # Check for abort during pause
                        abort_key = check_keyboard_input()
                        if abort_key in (' ', 'r'):
                            print(" Resuming now!\n")
                            break
                        print(f"{i}... ", end="", flush=True)
                        time.sleep(1)
                    else:
                        print("GO!\n")
                else:
                    print("Failed to capture snapshot frame")

                # Clear any buffered input
                while select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)

                continue

            # Capture frame
            try:
                frame = capture_frame(camera, camera_type)
                if frame is None:
                    print("Failed to capture frame (returned None)")
                    continue
            except Exception as e:
                print(f"Camera capture error: {e}")
                time.sleep(0.1)
                continue

            # Resize to display dimensions
            small_frame = resize_frame(frame, display_mode)

            # Apply black and white filter if enabled
            if black_and_white_mode:
                small_frame = apply_black_and_white(small_frame)

            # Debug: Save the resized frame to last.bmp
            cv2.imwrite("last.bmp", small_frame)

            # Convert to RGB565 bytes
            frame_bytes = convert_to_rgb565(small_frame)

            # Send to Matrix Portal
            bytes_sent = send_frame_usb(usb_serial, frame_bytes)

            # Frame timing
            frame_count += 1
            if frame_count == 1:
                print(f"First frame sent: {bytes_sent} bytes")
            if debug_mode and frame_count % 10 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                bw_status = " [B&W]" if black_and_white_mode else ""
                mode_status = f" [{display_mode.upper()}]" if display_mode != 'landscape' else ""
                print(f"Frames: {frame_count}, FPS: {fps:.1f}, Bytes sent: {bytes_sent}/{len(frame_bytes)}{bw_status}{mode_status}")

            # Frame rate control (optional)
            if ENABLE_FRAME_LIMITING:
                elapsed = time.time() - loop_start
                frame_time = 1.0 / TARGET_FPS
                sleep_time = max(0, frame_time - elapsed)
                time.sleep(sleep_time)

            if args.frames > 0 and frame_count >= args.frames:
                print(f"Reached target of {args.frames} frames. Stopping.")
                break

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # Restore terminal settings (MUST happen or terminal stays in raw mode)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)
        # Release camera (OpenCV needs explicit release, picamera2 does not)
        if camera_type == "opencv":
            camera.release()
        # picamera2 is automatically cleaned up
        if usb_serial and usb_serial.is_open:
            usb_serial.close()


if __name__ == "__main__":
    main()
