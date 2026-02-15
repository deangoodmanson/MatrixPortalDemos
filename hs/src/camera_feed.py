#!/usr/bin/env python3
"""
===========================================
LED MATRIX CAMERA FEED
High School Learning Version (Unified)
===========================================

This program captures video from the Pi Camera (or USB webcam)
and displays it on a 64x32 LED matrix in real-time!

WHAT YOU'LL LEARN:
- How digital cameras capture images
- How images are stored as numbers (pixels)
- How to resize and crop images
- How colors work (RGB and RGB565)
- How to send data to hardware devices
- How to handle keyboard input
- How to use text-to-speech

FEATURES:
- Display orientations (landscape, portrait)
- Processing modes (center crop, stretch, fit)
- Black & white mode toggle
- Snapshot with countdown
- Avatar capture mode with voice prompts

RASPBERRY PI CAMERA OPTIONS:
- Pi Camera Module: Plugs into the ribbon cable connector
- USB Webcam: Plugs into any USB port

The program automatically tries the Pi Camera first, then USB webcam!

REQUIREMENTS:
- Python 3
- OpenCV (cv2) - for camera and image processing
- picamera2 - for Raspberry Pi camera (optional)
- pyserial - for talking to the LED matrix
- numpy - for fast math on images

===========================================
"""

# ===========================================
# STEP 1: IMPORT THE TOOLS WE NEED
# ===========================================
# Think of these like importing LEGO sets before building.
# Each "import" gives us new abilities.

import time                         # For timing and delays
import numpy as np                  # For fast math on images (np = "numpy")
import cv2                          # OpenCV - for camera and images
import serial                       # For talking to USB devices
import serial.tools.list_ports     # For finding USB devices
import sys                          # For system-level stuff (stdin, exit)
import select                       # For checking if keyboard input is ready
import os                           # For file and directory operations
from typing import Optional, Tuple, Any  # For type hints (helps understand what data types we use)
import json                         # For saving data in JSON format
from datetime import datetime       # For timestamps

# ===========================================
# ADVANCED IMPORTS (Unix/Mac/Linux)
# ===========================================
# These modules let us read single keypresses without waiting for Enter.
# This is an ADVANCED concept - normally input() waits for Enter.
#
# HOW IT WORKS:
# - 'tty' controls terminal behavior
# - 'termios' stores/restores terminal settings
# - We switch to "cbreak" mode where each keypress is sent immediately
#
# NOTE: Raspberry Pi uses Linux, so these work here!

import tty
import termios

# ===========================================
# ADVANCED IMPORTS (Text-to-Speech)
# ===========================================
# These modules let us make the computer talk!
# - 'subprocess' runs external programs (like 'espeak-ng' on Linux)
# - 'platform' tells us which operating system we're on

import subprocess
import platform

from config import (                # Our settings file
    MATRIX_WIDTH,
    MATRIX_HEIGHT,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    TARGET_FPS
)

# ===========================================
# SETTINGS YOU CAN CHANGE
# ===========================================

# Set this to True to see extra information while running
DEBUG_MODE = True

# Set this to True to show a preview window of what the camera sees
# NOTE: Set to False if running on a Raspberry Pi without a monitor!
SHOW_PREVIEW = True

# The "magic word" we send before each frame so the LED matrix
# knows a new picture is coming (like saying "incoming!")
FRAME_HEADER = b'IMG1'

# How fast to send data (2 million bits per second!)
BAUD_RATE = 4000000

# How long to show each countdown number (in seconds)
COUNTDOWN_DURATION = 0.5

# ===========================================
# DISPLAY MODES
# ===========================================
# These control how the camera image is fit into the LED matrix.
# The matrix is 64 pixels wide and 32 pixels tall (2:1 ratio).
# Most cameras capture at 4:3 ratio (like 640x480).
# We need to decide: crop, stretch, or add black bars?

ORIENTATIONS = ['landscape', 'portrait']
PROCESSING_MODES = ['center', 'stretch', 'fit']

# Current settings (these can be changed with keyboard commands)
orientation = 'landscape'         # Display orientation (wide or tall)
processing_mode = 'center'        # How to fit the image (crop, stretch, or fit)
black_and_white_mode = False      # Color or grayscale?
debug_output = True               # Show frame rate info?

# ===========================================
# AVATAR CAPTURE POSES
# ===========================================
# These are the poses we'll guide the user through when creating an avatar.
# Each entry is: (angle, expression, what to say)

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


# ===========================================
# FUNCTION: Set up the camera
# ===========================================
def setup_camera(camera_number: int = 0) -> Tuple[Any, str]:
    """
    Connect to the camera and get it ready to take pictures.

    UNIFIED CAMERA SETUP:
    - First, we try to use the Pi Camera (picamera2 library)
    - If that doesn't work (or on Mac/PC), we fall back to a USB webcam

    RETURNS:
    - A tuple of (camera_object, camera_type)
    - camera_type is either "picamera" or "opencv"
    """
    print("=" * 50)
    print("STEP 1: Setting up the camera")
    print("=" * 50)

    # Try the Pi Camera first
    try:
        from picamera2 import Picamera2

        print("  Trying Pi Camera...")
        picam = Picamera2()

        # Configure the camera
        config = picam.create_preview_configuration(
            main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT)}
        )
        picam.configure(config)
        picam.start()

        print("  Pi Camera is ready!")
        return picam, "picamera"

    except Exception as error:
        print(f"  Pi Camera not available: {error}")
        print("  Trying USB webcam instead...")

    # Fall back to USB webcam
    print(f"  Opening USB camera #{camera_number}...")
    camera = cv2.VideoCapture(camera_number)

    if not camera.isOpened():
        print("  ERROR: Could not open any camera!")
        print("  ")
        print("  TROUBLESHOOTING:")
        print("  - Is the Pi Camera ribbon cable connected properly?")
        print("  - Did you enable the camera in raspi-config?")
        print("  - Is a USB webcam plugged in?")
        print("  - Is another program using the camera?")
        raise RuntimeError("Failed to open camera")

    # Tell the camera what resolution we want
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    print("  USB webcam is ready!")
    return camera, "opencv"


# ===========================================
# FUNCTION: Capture one picture
# ===========================================
def capture_frame(camera: Any, camera_type: str) -> Optional[np.ndarray]:
    """
    Take a single picture from the camera.

    WHAT'S HAPPENING:
    - We ask the camera to capture one frame (picture)
    - The camera returns the image as a big grid of numbers
    - Each pixel has 3 numbers: the color values

    NOTE FOR PI CAMERA:
    - Pi Camera returns RGB format (Red-Green-Blue)
    - USB cameras return BGR format (Blue-Green-Red)
    - We convert Pi Camera to BGR to keep things consistent

    RETURNS:
    - A frame (image) as a numpy array, or None if it failed
    """
    if camera_type == "picamera":
        # Pi Camera capture
        frame = camera.capture_array()
        # Convert from RGB to BGR for consistency with OpenCV
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    else:
        # USB webcam capture
        success, frame = camera.read()
        if not success:
            return None

    return frame


# ===========================================
# FUNCTION: Resize the image with orientation and processing modes
# ===========================================
def resize_frame(frame: np.ndarray, orient: str = 'landscape', proc_mode: str = 'center') -> np.ndarray:
    """
    Resize and/or crop the camera image to fit the LED matrix.

    WHY WE NEED THIS:
    - Camera captures 640x480 = 307,200 pixels (4:3 ratio)
    - LED matrix only has 64x32 = 2,048 pixels (2:1 ratio)
    - The shapes don't match! We need to decide what to do.

    ORIENTATIONS:
    =============
    LANDSCAPE: Horizontal display (wide)
    PORTRAIT:  Vertical display (tall, rotates 90 degrees)

    PROCESSING MODES:
    =================
    CENTER (default):
    - Crops from the CENTER to match aspect ratio
    - Clips edges based on orientation
    - Good for: keeping the main subject centered

    STRETCH:
    - Stretches entire image to fit (may distort)
    - No cropping, but proportions change
    - Good for: seeing everything

    FIT:
    - Shrinks to fit WITHOUT distortion
    - Adds black bars to fill empty space
    - Good for: no distortion, no cropping

    RETURNS:
    - A 64x32 pixel image ready for the LED matrix
    """
    height, width = frame.shape[:2]  # Get image dimensions

    # ===== STEP 1: Apply processing mode =====
    if proc_mode == 'fit':
        # Letterbox mode - maintain aspect ratio
        scale_width = MATRIX_WIDTH / width
        scale_height = MATRIX_HEIGHT / height
        scale = min(scale_width, scale_height)

        new_width = int(width * scale)
        new_height = int(height * scale)

        resized = cv2.resize(frame, (new_width, new_height))

        # Create black canvas
        canvas = np.zeros((MATRIX_HEIGHT, MATRIX_WIDTH, 3), dtype=np.uint8)

        # Center the image
        x_offset = (MATRIX_WIDTH - new_width) // 2
        y_offset = (MATRIX_HEIGHT - new_height) // 2

        canvas[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = resized
        processed = canvas

    elif proc_mode == 'stretch':
        # Stretch mode - just resize directly
        processed = cv2.resize(frame, (MATRIX_WIDTH, MATRIX_HEIGHT))

    else:  # 'center' (default)
        # Center crop to target aspect ratio
        target_aspect = MATRIX_WIDTH / MATRIX_HEIGHT
        current_aspect = width / height

        if current_aspect > target_aspect:
            # Image is wider than target, crop width (left and right)
            new_width = int(height * target_aspect)
            start_x = (width - new_width) // 2
            cropped = frame[0:height, start_x:start_x + new_width]
        else:
            # Image is taller than target, crop height (top and bottom)
            new_height = int(width / target_aspect)
            start_y = (height - new_height) // 2
            cropped = frame[start_y:start_y + new_height, 0:width]

        processed = cv2.resize(cropped, (MATRIX_WIDTH, MATRIX_HEIGHT))

    # ===== STEP 2: Apply orientation (rotation for portrait) =====
    if orient == 'portrait':
        # Rotate 90 degrees clockwise for portrait orientation
        processed = cv2.rotate(processed, cv2.ROTATE_90_CLOCKWISE)

    return processed


# ===========================================
# FUNCTION: Convert to black and white
# ===========================================
def apply_black_and_white(frame: np.ndarray) -> np.ndarray:
    """
    Convert a color image to black and white (grayscale).

    HOW IT WORKS:
    1. Convert BGR (color) to GRAY (single channel)
    2. Convert back to BGR (3 channels, but all the same value)

    Why convert back to BGR? Because our RGB565 function expects
    3 color channels. We just make R=G=B for each pixel.

    RETURNS:
    - A grayscale image in BGR format
    """
    # Convert to grayscale (1 channel)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Convert back to BGR (3 channels, all the same)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


# ===========================================
# FUNCTION: Convert colors to RGB565
# ===========================================
def convert_to_rgb565(frame: np.ndarray) -> bytes:
    """
    Convert the image colors to RGB565 format.

    WHY RGB565?
    ===========
    Normal images use 24 bits per pixel:
    - 8 bits for Red   (256 shades: 0-255)
    - 8 bits for Green (256 shades: 0-255)
    - 8 bits for Blue  (256 shades: 0-255)
    - Total: 16.7 MILLION possible colors!

    But that's a lot of data to send. RGB565 uses only 16 bits:
    - 5 bits for Red   (32 shades: 0-31)
    - 6 bits for Green (64 shades: 0-63) - extra because humans see green better!
    - 5 bits for Blue  (32 shades: 0-31)
    - Total: 65,536 colors (still plenty!)

    This is the same format used by Game Boy Advance and old flip phones!

    HOW IT WORKS:
    =============
    We reduce each color channel:
    - Red:   0-255 becomes 0-31  (divide by 8)
    - Green: 0-255 becomes 0-63  (divide by 4)
    - Blue:  0-255 becomes 0-31  (divide by 8)

    Then we pack them into 16 bits:
    - Red goes in bits 11-15   (multiply by 2048)
    - Green goes in bits 5-10  (multiply by 32)
    - Blue goes in bits 0-4    (no multiplication needed)

    RETURNS:
    - Bytes ready to send to the LED matrix
    """

    # Step 1: Convert BGR to RGB
    # OpenCV uses Blue-Green-Red order, but we need Red-Green-Blue
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Step 2: Get each color channel
    red = rgb[:, :, 0]     # Red channel (0-255)
    green = rgb[:, :, 1]   # Green channel (0-255)
    blue = rgb[:, :, 2]    # Blue channel (0-255)

    # Step 3: Reduce to RGB565 levels using division
    # (Division is easier to understand than bit-shifting)
    red_5bit = (red // 8).astype(np.uint16)      # 256 levels -> 32 levels
    green_6bit = (green // 4).astype(np.uint16)  # 256 levels -> 64 levels
    blue_5bit = (blue // 8).astype(np.uint16)    # 256 levels -> 32 levels

    # Step 4: Pack into 16-bit values
    # RRRRR GGGGGG BBBBB
    red_shifted = red_5bit * 2048      # Move red to bits 11-15
    green_shifted = green_6bit * 32    # Move green to bits 5-10
    blue_shifted = blue_5bit           # Blue stays at bits 0-4

    # Combine them all!
    rgb565 = red_shifted + green_shifted + blue_shifted

    # Step 5: Convert to bytes (little-endian)
    frame_bytes = rgb565.astype('<u2').tobytes()

    return frame_bytes


# ===========================================
# FUNCTION: Find the LED Matrix
# ===========================================
def find_matrix_portal() -> Optional[str]:
    """
    Search for the Matrix Portal device on USB.

    RETURNS:
    - The path to the serial port (like "/dev/ttyACM0")
    - Or None if we can't find it
    """
    print("=" * 50)
    print("STEP 2: Finding the LED Matrix")
    print("=" * 50)

    # Get list of all USB serial ports
    ports = serial.tools.list_ports.comports()

    print("  Available USB devices:")
    for port in ports:
        print(f"    - {port.device}: {port.description}")

    # Look for Matrix Portal
    matrix_ports = []
    for port in ports:
        if "CircuitPython" in port.description or "Matrix Portal" in port.description:
            matrix_ports.append(port)

    if not matrix_ports:
        print("  Matrix Portal not found!")
        return None

    # If multiple ports found, use the one with the higher number
    if len(matrix_ports) > 1:
        matrix_ports.sort(key=lambda p: p.device)
        selected = matrix_ports[-1].device
    else:
        selected = matrix_ports[0].device

    print(f"  Found Matrix Portal at: {selected}")
    return selected


# ===========================================
# FUNCTION: Connect to the LED Matrix
# ===========================================
def setup_usb_serial() -> Optional[serial.Serial]:
    """
    Establish a connection to the LED Matrix.

    RETURNS:
    - A serial connection object, or None if it failed
    """
    port = find_matrix_portal()
    if port is None:
        return None

    print(f"  Connecting at {BAUD_RATE:,} bits per second...")

    try:
        connection = serial.Serial(
            port,
            baudrate=BAUD_RATE,
            timeout=0.1,
            write_timeout=0.5,
            rtscts=False,
            dsrdtr=False
        )
        time.sleep(0.5)
        print(f"  Connected successfully!")
        return connection

    except Exception as error:
        print(f"  ERROR: Could not connect: {error}")
        return None


# ===========================================
# FUNCTION: Send a frame to the LED Matrix
# ===========================================
def send_frame(serial_connection: serial.Serial, frame_bytes: bytes) -> int:
    """
    Send one frame of image data to the LED Matrix.

    RETURNS:
    - Number of bytes sent, or 0 if failed
    """
    if serial_connection is None or not serial_connection.is_open:
        return 0

    serial_connection.write(FRAME_HEADER)
    bytes_sent = serial_connection.write(frame_bytes)
    serial_connection.flush()

    return bytes_sent


# ===========================================
# FUNCTION: Check for keyboard input
# ===========================================
def check_keyboard() -> Optional[str]:
    """
    Check if a key has been pressed (without waiting).

    ADVANCED CONCEPT: Non-blocking I/O
    ==================================
    Normally, input() BLOCKS - it waits until you press Enter.
    We want to check for keys WITHOUT stopping the video feed.

    HOW IT WORKS:
    - select.select() checks if there's data ready to read
    - If data is ready, we read ONE character
    - If no data, we return None immediately

    The terminal must be in "cbreak" mode for this to work
    (set up in main() using tty.setcbreak)

    RETURNS:
    - A single character if a key was pressed
    - None if no key was pressed
    """
    # select.select(read_list, write_list, error_list, timeout)
    # We only care about reading from stdin, with 0 second timeout
    if select.select([sys.stdin], [], [], 0)[0]:
        # There's input waiting! Read one character.
        char = sys.stdin.read(1).lower()
        return char
    return None


# ===========================================
# FUNCTION: Speak text out loud
# ===========================================
def speak(text: str) -> None:
    """
    Make the computer speak using text-to-speech.

    ADVANCED CONCEPT: Running External Programs
    ===========================================
    Python can run other programs on your computer using subprocess.
    We use this to run the text-to-speech command.

    Different operating systems have different TTS commands:
    - macOS: 'say' command with fun voices like "Zarvox" (robot)
    - Linux (Raspberry Pi): 'espeak-ng' with robotic settings
    - Windows: requires the pyttsx3 library

    HOW IT WORKS:
    - platform.system() tells us which OS we're on
    - subprocess.run() executes the command
    - We use check=False so errors don't crash our program
    """
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            # "Zarvox" is a classic robot voice!
            subprocess.run(["say", "-v", "Zarvox", text], check=False)

        elif system == "Linux":  # Raspberry Pi uses Linux
            # espeak-ng with robotic settings
            # Install with: sudo apt install espeak-ng
            subprocess.run(
                ["espeak-ng", "-v", "en+m3", "-s", "130", "-p", "30", text],
                check=False,
                stderr=subprocess.DEVNULL  # Hide error messages
            )

        else:  # Windows
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 130)
                engine.say(text)
                engine.runAndWait()
            except ImportError:
                print("  (Voice unavailable - install pyttsx3)")

    except FileNotFoundError:
        # TTS program not installed, just skip
        pass
    except Exception:
        # Any other error, continue without voice
        pass


# ===========================================
# FUNCTION: Draw border around frame
# ===========================================
def draw_border(frame: np.ndarray, color: Tuple[int, int, int] = (255, 0, 0)) -> np.ndarray:
    """
    Draw single-pixel border around frame.

    Args:
        frame: BGR image as numpy array (will be copied).
        color: BGR color for the border.

    Returns:
        New frame with border.
    """
    bordered = frame.copy()
    height, width = bordered.shape[:2]

    # Draw 1-pixel border around all edges
    bordered[0, :] = color  # Top edge
    bordered[height-1, :] = color  # Bottom edge
    bordered[:, 0] = color  # Left edge
    bordered[:, width-1] = color  # Right edge

    return bordered


# ===========================================
# FUNCTION: Save a snapshot
# ===========================================
def save_snapshot(frame: np.ndarray, frame_bytes: bytes, orient: str, debug_mode: bool = False) -> str:
    """
    Save the current frame to disk.

    WHAT'S SAVED:
    - A .bmp snapshot file (viewable in any image viewer, properly oriented for PC viewing)
    - Debug files (only if debug_mode=True):
      - A raw .bmp file showing exact LED matrix frame (64x32)
      - A .bin file with raw RGB565 data

    The filename includes a timestamp so each snapshot is unique.

    RETURNS:
    - The filename of the saved snapshot image
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create properly oriented snapshot for viewing on PC
    if orient == "portrait":
        # Rotate back 90° CCW so it appears upright (32x64 tall)
        viewer_frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        # Landscape stays as-is (64x32 wide)
        viewer_frame = frame

    # Always save the viewer-oriented snapshot
    snapshot_filename = f"snapshot_{timestamp}.bmp"
    cv2.imwrite(snapshot_filename, viewer_frame)

    print(f"\n{'='*60}")
    print(f"SNAPSHOT SAVED:")
    print(f"  Snapshot: {snapshot_filename}")

    # Debug files (only in debug mode)
    if debug_mode:
        # Save raw LED matrix frame (64x32 with rotation applied)
        debug_filename = f"snapshot_{timestamp}_raw.bmp"
        cv2.imwrite(debug_filename, frame)
        print(f"  Debug raw: {debug_filename}")

        # Save RGB565 binary data
        rgb565_filename = f"snapshot_{timestamp}_rgb565.bin"
        with open(rgb565_filename, 'wb') as f:
            f.write(frame_bytes)
        print(f"  Debug RGB565: {rgb565_filename}")

    print(f"{'='*60}\n")

    return snapshot_filename


# ===========================================
# FUNCTION: Run snapshot countdown
# ===========================================
def run_snapshot(camera: Any, camera_type: str, serial_connection: serial.Serial, orient: str, proc_mode: str, is_bw: bool) -> bool:
    """
    Take a snapshot with a 3-2-1 countdown.

    HOW IT WORKS:
    1. Display countdown (3, 2, 1) on the LED matrix
    2. Capture the frame when countdown finishes
    3. Save to disk
    4. Pause for a few seconds to admire the shot

    The user can press SPACE or R to cancel/resume.

    RETURNS:
    - True if snapshot was taken, False if cancelled
    """
    print("\n=== SNAPSHOT MODE (press any key to cancel) ===")
    speak("Get ready")

    # Countdown loop
    last_small_frame = None

    for countdown in [3, 2, 1]:
        print(f"  {countdown}...")
        countdown_start = time.time()

        # Show this number for COUNTDOWN_DURATION seconds
        while time.time() - countdown_start < COUNTDOWN_DURATION:
            # Check for cancel
            key = check_keyboard()
            if key in (' ', 'r'):
                print("  Cancelled!")
                speak("Cancelled")
                return False

            # Capture and display with countdown overlay
            frame = capture_frame(camera, camera_type)
            if frame is None:
                continue

            small_frame = resize_frame(frame, orient, proc_mode)
            if is_bw:
                small_frame = apply_black_and_white(small_frame)

            # Save the last frame from countdown "1" for the snapshot
            if countdown == 1:
                last_small_frame = small_frame.copy()
                # Show blue border during "1" countdown to indicate capture framing
                small_frame = draw_border(small_frame, color=(255, 0, 0))  # Blue in BGR

            # Add countdown number to the frame
            overlay = small_frame.copy()

            if orient == 'portrait':
                # For portrait mode, draw rotated text
                text = str(countdown)
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]

                # Create temporary canvas for text
                temp = np.zeros((text_size[1] + 10, text_size[0] + 10, 3), dtype=np.uint8)
                cv2.putText(temp, text, (5, text_size[1] + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                # Rotate text 90° counter-clockwise
                rotated_text = cv2.rotate(temp, cv2.ROTATE_90_COUNTERCLOCKWISE)

                # Position in lower right corner
                h, w = rotated_text.shape[:2]
                y_start = MATRIX_HEIGHT - h - 2
                x_start = MATRIX_WIDTH - w - 2

                # Overlay the rotated text (only non-black pixels)
                mask = np.any(rotated_text > 0, axis=2)
                overlay[y_start:y_start+h, x_start:x_start+w][mask] = rotated_text[mask]
            else:
                # Landscape mode - position in lower left corner
                cv2.putText(
                    overlay,
                    str(countdown),
                    (2, MATRIX_HEIGHT - 4),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),  # Red color (BGR)
                    1
                )

            frame_bytes = convert_to_rgb565(overlay)
            send_frame(serial_connection, frame_bytes)

            time.sleep(0.01)

    # Use the last frame from countdown "1" as the snapshot
    print("  SNAP!")
    speak("Got it")

    if last_small_frame is not None:
        # Add blue border around frozen frame
        small_frame = draw_border(last_small_frame, color=(255, 0, 0))  # Blue in BGR

        frame_bytes = convert_to_rgb565(small_frame)
        save_snapshot(small_frame, frame_bytes, orient, debug_output)
        send_frame(serial_connection, frame_bytes)

        # Pause to admire
        print("  Pausing for 5 seconds (press any key to skip)...")
        for i in range(5, 0, -1):
            key = check_keyboard()
            if key in (' ', 'r'):
                print("  Resuming!")
                break
            print(f"  {i}...", end=" ", flush=True)
            time.sleep(1)
        print()

    return True


# ===========================================
# FUNCTION: Avatar capture mode
# ===========================================
def run_avatar_capture(camera: Any, camera_type: str, serial_connection: serial.Serial, orient: str, proc_mode: str) -> list:
    """
    Guided avatar capture session with voice prompts.

    WHAT THIS DOES:
    - Walks you through 18 different poses
    - Speaks instructions for each pose
    - Saves all images to a folder with organized names

    This is useful for creating animated avatars or AI training data.

    CONTROLS:
    - SPACE = Capture this pose
    - S = Skip this pose
    - R = Repeat the voice prompt
    - Q = Quit avatar mode

    RETURNS:
    - List of captured file information
    """
    # Create output folder
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
    print("\nTip: Use 'P' before starting for portrait mode!")
    print("=" * 60)

    speak("Avatar capture mode. Get ready.")
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

        # Speak the instruction
        speak(prompt)

        # Wait for capture
        waiting = True
        while waiting:
            # Show live preview
            frame = capture_frame(camera, camera_type)
            if frame is not None:
                small_frame = resize_frame(frame, orient, proc_mode)
                frame_bytes = convert_to_rgb565(small_frame)
                send_frame(serial_connection, frame_bytes)

            # Check for input
            if select.select([sys.stdin], [], [], 0.01)[0]:
                key = sys.stdin.read(1).lower()

                if key == ' ':
                    # Capture!
                    if frame is not None:
                        cv2.imwrite(filepath, small_frame)
                        rgb565_path = filepath.replace('.bmp', '_rgb565.bin')
                        with open(rgb565_path, 'wb') as f:
                            f.write(frame_bytes)

                        captured.append({
                            "pose": pose_num,
                            "angle": angle,
                            "expression": expression,
                            "file": filename
                        })
                        print(f"  Captured!")
                        speak("Got it")
                        waiting = False
                    else:
                        speak("Failed, try again")

                elif key == 's':
                    skipped.append({"pose": pose_num, "angle": angle, "expression": expression})
                    print(f"  Skipped")
                    speak("Skipped")
                    waiting = False

                elif key == 'r':
                    speak(prompt)

                elif key == 'q':
                    print("\n  Avatar capture cancelled.")
                    speak("Cancelled")
                    _save_manifest(avatar_dir, captured, skipped, session_time)
                    return captured

    # Done!
    print("\n" + "=" * 60)
    print("   AVATAR CAPTURE COMPLETE!")
    print("=" * 60)
    print(f"\nCaptured: {len(captured)} poses")
    print(f"Skipped:  {len(skipped)} poses")
    print(f"Location: {avatar_dir}/")

    speak(f"Complete! {len(captured)} poses saved.")
    _save_manifest(avatar_dir, captured, skipped, session_time)

    return captured


def _save_manifest(avatar_dir: str, captured: list, skipped: list, session_time: str) -> None:
    """Save a JSON file listing all captured poses."""
    manifest = {
        "session": session_time,
        "total_poses": len(AVATAR_POSES),
        "captured": captured,
        "skipped": skipped
    }
    path = os.path.join(avatar_dir, "manifest.json")
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest saved: {path}")


# ===========================================
# FUNCTION: Show preview windows
# ===========================================
def show_preview(original_frame: np.ndarray, small_frame: np.ndarray) -> None:
    """
    Display preview windows so you can see what's happening.

    NOTE: On a headless Raspberry Pi (no monitor), keep SHOW_PREVIEW = False!
    """
    if not SHOW_PREVIEW:
        return

    cv2.imshow("Camera View", original_frame)

    # Enlarge the tiny matrix view (10x bigger)
    enlarged = cv2.resize(
        small_frame,
        (MATRIX_WIDTH * 10, MATRIX_HEIGHT * 10),
        interpolation=cv2.INTER_NEAREST  # Blocky pixels
    )
    cv2.imshow("LED Matrix View (10x)", enlarged)


# ===========================================
# FUNCTION: Print help
# ===========================================
def print_help(orient: str, proc_mode: str, bw: bool, debug: bool) -> None:
    """Print the help message with current settings."""
    print("")
    print("=" * 60)
    print("KEYBOARD COMMANDS:")
    print("  Orientation: L=landscape  P=portrait")
    print("  Processing:  C=center  S=stretch  F=fit")
    print("  Effects:     B=toggle B&W/Color")
    print("  Actions:     SPACE=snapshot  V=avatar")
    print("  System:      D=debug  R=reset  H=help  Q=quit")
    print("")
    bw_str = "B&W" if bw else "Color"
    debug_str = "ON" if debug else "OFF"
    print(f"  Current: {orient.title()} + {proc_mode.title()}, {bw_str}, Debug={debug_str}")
    print("=" * 60)
    print("")


# ===========================================
# MAIN PROGRAM
# ===========================================
def main() -> None:
    """
    The main program that runs everything!

    ADVANCED CONCEPT: Terminal Modes
    ================================
    To read single keypresses (without Enter), we need to change
    how the terminal works. This is called "cbreak" mode.

    IMPORTANT: We MUST restore the terminal settings when we exit,
    or your terminal will be broken! That's why we use try/finally.
    """
    global orientation, processing_mode, black_and_white_mode, debug_output

    # ===========================================
    # ADVANCED: Save and modify terminal settings
    # ===========================================
    # This lets us read single keypresses without Enter
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    print("")
    print("=" * 50)
    print("   LED MATRIX CAMERA FEED")
    print("   High School Learning Version (Raspberry Pi)")
    print("=" * 50)
    print("")
    print(f"Matrix size: {MATRIX_WIDTH} x {MATRIX_HEIGHT} pixels")
    print(f"Bytes per frame: {MATRIX_WIDTH * MATRIX_HEIGHT * 2}")
    print("")

    # Set up camera (tries Pi Camera first, then USB)
    camera, camera_type = setup_camera()
    print(f"  Using camera type: {camera_type}")

    # Connect to LED matrix
    serial_connection = setup_usb_serial()

    if serial_connection is None:
        print("\nWARNING: LED Matrix not connected!")
        print("Running in preview-only mode...")

    print("")
    print("=" * 50)
    print("STEP 3: Starting the camera feed!")
    print("=" * 50)
    print("")
    print_help(orientation, processing_mode, black_and_white_mode, debug_output)
    print("Press Ctrl+C to force quit")
    print("")

    frame_count = 0
    start_time = time.time()

    # ===========================================
    # ADVANCED: Enable single-keypress mode
    # ===========================================
    tty.setcbreak(sys.stdin.fileno())

    try:
        while True:
            # Check for keyboard input
            key = check_keyboard()

            # === ORIENTATION KEYS ===
            if key == 'l':
                orientation = 'landscape'
                print("\n=== ORIENTATION: LANDSCAPE (Wide) ===\n")
                continue

            if key == 'p':
                orientation = 'portrait'
                print("\n=== ORIENTATION: PORTRAIT (Tall) ===\n")
                continue

            # === PROCESSING MODE KEYS ===
            if key == 'c':
                processing_mode = 'center'
                print("\n=== PROCESSING MODE: CENTER (Crop from center) ===\n")
                continue

            if key == 's':
                processing_mode = 'stretch'
                print("\n=== PROCESSING MODE: STRETCH (Distort to fit) ===\n")
                continue

            if key == 'f':
                processing_mode = 'fit'
                print("\n=== PROCESSING MODE: FIT (Letterbox) ===\n")
                continue

            # === EFFECT KEYS ===
            if key == 'b':
                black_and_white_mode = not black_and_white_mode
                mode_str = "BLACK & WHITE" if black_and_white_mode else "COLOR"
                print(f"\n=== {mode_str} MODE ===\n")
                continue

            # === RESET ===
            if key == 'r':
                orientation = 'landscape'
                processing_mode = 'center'
                black_and_white_mode = False
                debug_output = True
                print("\n=== RESET TO DEFAULTS ===")
                print("Orientation=landscape, Processing=center, Color, Debug=ON\n")
                continue

            # === ACTION KEYS ===
            if key == 'd':
                debug_output = not debug_output
                status = "ON" if debug_output else "OFF"
                print(f"\n=== DEBUG: {status} ===\n")
                continue

            if key == 'h':
                print_help(orientation, processing_mode, black_and_white_mode, debug_output)
                continue

            if key == 'q':
                print("\n=== QUIT ===\n")
                break

            if key == ' ':
                run_snapshot(camera, camera_type, serial_connection, orientation, processing_mode, black_and_white_mode)
                # Clear any buffered input
                while select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)
                continue

            if key == 'v':
                run_avatar_capture(camera, camera_type, serial_connection, orientation, processing_mode)
                while select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)
                continue

            # === MAIN CAPTURE LOOP ===
            frame = capture_frame(camera, camera_type)
            if frame is None:
                print("WARNING: Failed to capture frame")
                continue

            # Process the frame
            small_frame = resize_frame(frame, orientation, processing_mode)

            if black_and_white_mode:
                small_frame = apply_black_and_white(small_frame)

            # Convert and send
            frame_bytes = convert_to_rgb565(small_frame)
            bytes_sent = send_frame(serial_connection, frame_bytes)

            # Show preview
            show_preview(frame, small_frame)

            # Statistics
            frame_count += 1
            if debug_output and frame_count % 10 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                mode_str = f"[{orientation[0].upper()}{processing_mode[0].upper()}]"
                bw_str = " [B&W]" if black_and_white_mode else ""
                print(f"  Frames: {frame_count}, FPS: {fps:.1f}, Bytes: {bytes_sent}{mode_str}{bw_str}")

            # Check for quit in preview window
            if SHOW_PREVIEW:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")

    finally:
        # ===========================================
        # CRITICAL: Restore terminal settings!
        # ===========================================
        # If we don't do this, your terminal will be broken!
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)

        # Clean up
        print("\nCleaning up...")
        if camera_type == "opencv":
            camera.release()
        # Note: picamera2 doesn't need explicit release

        if serial_connection and serial_connection.is_open:
            serial_connection.close()
        if SHOW_PREVIEW:
            cv2.destroyAllWindows()
        print("Goodbye!")


# ===========================================
# RUN THE PROGRAM
# ===========================================
if __name__ == "__main__":
    main()
