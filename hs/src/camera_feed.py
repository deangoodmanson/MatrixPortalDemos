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

import argparse                      # For command-line arguments
import math                         # For math functions like ceil()
from enum import Enum               # For creating named constants (enumerations)
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
    MAX_BRIGHTNESS,
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
mirror_mode = False               # Flip the image left-to-right (like a mirror)?
debug_output = True               # Show frame rate info?

# ===========================================
# LED PREVIEW RENDER MODES
# ===========================================
# These control how each LED is drawn in the preview window.
# Toggle with the 'o' key.
#
# A real LED matrix has small round lights (LEDs) arranged in a grid.
# The default view shows plain squares, but we can make it look more
# realistic with circles and gaps between each LED.
#
# WHAT IS AN ENUM?
# An Enum (enumeration) is a set of named constants.
# Instead of using plain numbers (0, 1, 2, 3) — which are hard to read —
# we give each value a meaningful name like SQUARES or CIRCLES_EDGE.
# Python's 'Enum' class is imported at the top of this file.

class RenderAlgorithm(Enum):
    """How each LED is drawn in the preview window.

    SQUARES:           Plain nearest-neighbour upscale — fast, blocky (default)
    CIRCLES:           Hard-edged circles; size controlled by led_size_pct (+/- keys)
    GAUSSIAN_RAW:      Raw panel emulation — gaussian blur, sigma≈18% cell (no diffuser)
    GAUSSIAN_DIFFUSED: Diffused panel emulation — gaussian blur, sigma≈27% cell (with diffuser)
    """
    SQUARES = 0
    CIRCLES = 1
    GAUSSIAN_RAW = 2
    GAUSSIAN_DIFFUSED = 3


# Human-readable labels shown when cycling algorithms with 'o'
ALGORITHM_LABELS = {
    RenderAlgorithm.SQUARES:           "squares",
    RenderAlgorithm.CIRCLES:           "circles (hard edge, size adjustable with +/-)",
    RenderAlgorithm.GAUSSIAN_RAW:      "raw panel emulation (gaussian, sigma≈18% cell)",
    RenderAlgorithm.GAUSSIAN_DIFFUSED: "diffused panel emulation (gaussian, sigma≈27% cell)",
}

# LED size steps (percentage of cell diameter) — only applies to CIRCLES
LED_SIZE_STEPS = [25, 50, 75, 100, 125, 150]

# Current render algorithm (changed with 'o' key)
render_algorithm = RenderAlgorithm.SQUARES

# Current LED size percentage (changed with +/- keys, only for CIRCLES)
led_size_pct = 100

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
# FUNCTION: List available cameras
# ===========================================
def list_available_cameras() -> list:
    """
    Detect and list all available cameras on the system.

    RETURNS:
    - A list of dictionaries with camera information
    """
    cameras = []

    # Check first 10 camera indices
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            backend = cap.getBackendName()

            cameras.append({
                "index": i,
                "type": "USB/OpenCV",
                "backend": backend,
                "resolution": f"{width}x{height}",
                "fps": fps if fps > 0 else "unknown",
            })
            cap.release()

    # Check for Pi Camera
    try:
        from picamera2 import Picamera2
        try:
            picam = Picamera2()
            camera_props = picam.camera_properties
            sensor_modes = picam.sensor_modes

            # Get default resolution from first sensor mode
            if sensor_modes:
                mode = sensor_modes[0]
                width = mode['size'][0]
                height = mode['size'][1]
                resolution = f"{width}x{height}"
            else:
                resolution = "unknown"

            cameras.append({
                "index": "Pi",
                "type": "Pi Camera",
                "backend": "libcamera",
                "resolution": resolution,
                "model": camera_props.get('Model', 'Unknown'),
                "fps": "varies",
            })
            picam.close()
        except Exception:
            pass
    except ImportError:
        pass

    return cameras


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

    except ImportError:
        print("  picamera2 not available in this environment.")
        print("  On Raspberry Pi OS, install with: sudo apt install python3-picamera2")
        print("  Then recreate venv with: uv venv --system-site-packages && uv sync")
        print("  Trying USB webcam instead...")
    except Exception as error:
        print(f"  Pi Camera error: {error}")
        print("  Trying USB webcam instead...")

    # Fall back to USB webcam
    print(f"  Opening USB camera #{camera_number}...")
    camera = cv2.VideoCapture(camera_number)

    if not camera.isOpened():
        # Try other camera indices if index 0 failed
        if camera_number == 0:
            print("  Camera index 0 failed, trying other indices...")
            for i in range(1, 5):
                camera = cv2.VideoCapture(i)
                if camera.isOpened():
                    print(f"  Found camera at index {i}")
                    camera_number = i
                    break
                camera.release()

    if not camera.isOpened():
        print("  ERROR: Could not open any camera!")
        print("  ")
        print("  TROUBLESHOOTING:")
        print("  - Is a USB webcam plugged in? Check with: lsusb")
        print("  - Is the Pi Camera enabled? Run: vcgencmd get_camera")
        print("  - List video devices: ls -l /dev/video*")
        print("  - Check what's using camera: fuser /dev/video0")
        print("  - Try system OpenCV: sudo apt install python3-opencv")
        print("  ")
        raise RuntimeError("Failed to open camera")

    # Only set resolution if explicitly configured (non-zero values)
    # Otherwise, use camera's native resolution (recommended!)
    if CAMERA_WIDTH > 0 and CAMERA_HEIGHT > 0:
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        # Verify what resolution was actually set
        actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if actual_width != CAMERA_WIDTH or actual_height != CAMERA_HEIGHT:
            print(f"  Note: Camera doesn't support {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
            print(f"  Using camera's resolution: {actual_width}x{actual_height}")
    else:
        # Using native resolution
        actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"  Using native resolution: {actual_width}x{actual_height}")

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

    # In portrait mode, swap target dimensions BEFORE processing so the
    # 90° rotation in step 2 produces the correct 64x32 output buffer.
    target_w = MATRIX_HEIGHT if orient == 'portrait' else MATRIX_WIDTH
    target_h = MATRIX_WIDTH if orient == 'portrait' else MATRIX_HEIGHT

    # ===== STEP 1: Apply processing mode =====
    if proc_mode == 'fit':
        # Letterbox mode - maintain aspect ratio
        scale_width = target_w / width
        scale_height = target_h / height
        scale = min(scale_width, scale_height)

        new_width = int(width * scale)
        new_height = int(height * scale)

        resized = cv2.resize(frame, (new_width, new_height))

        # Create black canvas
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)

        # Center the image
        x_offset = (target_w - new_width) // 2
        y_offset = (target_h - new_height) // 2

        canvas[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = resized
        processed = canvas

    elif proc_mode == 'stretch':
        # Stretch mode - just resize directly
        processed = cv2.resize(frame, (target_w, target_h))

    else:  # 'center' (default)
        # Center crop to target aspect ratio
        target_aspect = target_w / target_h
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

        processed = cv2.resize(cropped, (target_w, target_h))

    # ===== STEP 2: Apply orientation (rotation for portrait) =====
    if orient == 'portrait':
        # Rotate 90 degrees clockwise for portrait orientation
        processed = cv2.rotate(processed, cv2.ROTATE_90_CLOCKWISE)

    return processed


# ===========================================
# FUNCTION: Mirror the image
# ===========================================
def apply_mirror(frame: np.ndarray) -> np.ndarray:
    """
    Flip the image horizontally (left-to-right), like a mirror.

    WHY YOU'D USE THIS:
    - When someone stands in front of the display watching themselves,
      they expect their right hand to appear on the right side of the
      screen — just like a bathroom mirror. Without mirroring, their
      hand movements appear backwards.
    - Front-facing cameras (like a laptop webcam) usually default to
      mirror mode. Rear-facing cameras (like a phone back camera) do not.

    HOW IT WORKS:
    - cv2.flip(frame, 1) flips around the vertical axis (flipCode=1)
    - flipCode=0 would flip vertically (upside down)
    - flipCode=-1 would flip both axes

    RETURNS:
    - The horizontally flipped image
    """
    return cv2.flip(frame, 1)


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

        # Prevent DTR reset on CircuitPython devices
        # Must be done AFTER opening the port
        connection.dtr = False
        connection.rts = False

        # Wait for device to boot (CircuitPython takes ~1.5-2s to boot if reset)
        # If device didn't reset, this just ensures stability
        print("  Waiting for Matrix Portal to be ready...")
        time.sleep(2.0)

        # Flush any boot messages or garbage data
        connection.reset_input_buffer()
        connection.reset_output_buffer()

        print("  Connected successfully!")
        return connection

    except Exception as error:
        print(f"  ERROR: Could not connect: {error}")
        return None


# ===========================================
# FUNCTION: Send a frame to the LED Matrix
# ===========================================
def send_frame(serial_connection: Optional[serial.Serial], frame_bytes: bytes) -> int:
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
    print("SNAPSHOT SAVED:")
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
def run_snapshot(camera: Any, camera_type: str, serial_connection: Optional[serial.Serial], orient: str, proc_mode: str, is_bw: bool, is_mirror: bool = False, show_preview_enabled: bool = False, algorithm: RenderAlgorithm = RenderAlgorithm.SQUARES, led_size_pct: int = 100) -> bool:
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
            if key == ' ':
                print("  Cancelled!")
                speak("Cancelled")
                return False

            # Capture and display with countdown overlay
            frame = capture_frame(camera, camera_type)
            if frame is None:
                continue

            small_frame = resize_frame(frame, orient, proc_mode)
            if is_mirror:
                small_frame = apply_mirror(small_frame)
            if is_bw:
                small_frame = apply_black_and_white(small_frame)
            if MAX_BRIGHTNESS < 255:
                small_frame = np.minimum(small_frame, MAX_BRIGHTNESS).astype(np.uint8)

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

                # Rotate text 90° clockwise so it appears upright on the portrait display
                rotated_text = cv2.rotate(temp, cv2.ROTATE_90_CLOCKWISE)

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

            show_preview(frame, overlay, orient, show_preview_enabled, proc_mode, algorithm, led_size_pct)

            time.sleep(0.01)

    # Use the last frame from countdown "1" as the snapshot
    print("  SNAP!")
    speak("Got it")

    if last_small_frame is not None:
        # Save the clean frame (no border)
        frame_bytes = convert_to_rgb565(last_small_frame)
        save_snapshot(last_small_frame, frame_bytes, orient, debug_output)

        # Show blue border on the matrix display only
        small_frame = draw_border(last_small_frame, color=(255, 0, 0))  # Blue in BGR
        send_frame(serial_connection, convert_to_rgb565(small_frame))

        # Pause to admire
        print("  Pausing for 3 seconds (press space to skip)...")
        for i in range(3, 0, -1):
            key = check_keyboard()
            if key == ' ':
                print("  Resuming!")
                break
            print(f"  {i}...", end=" ", flush=True)
            time.sleep(1)
        print()

    return True


# ===========================================
# FUNCTION: Avatar capture mode
# ===========================================
def run_avatar_capture(camera: Any, camera_type: str, serial_connection: Optional[serial.Serial], orient: str, proc_mode: str) -> list:
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
                        print("  Captured!")
                        speak("Got it")
                        waiting = False
                    else:
                        speak("Failed, try again")

                elif key == 's':
                    skipped.append({"pose": pose_num, "angle": angle, "expression": expression})
                    print("  Skipped")
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
# FUNCTION: Render LED preview frame
# ===========================================

# ===========================================
# HELPER: Painter's-algorithm circle renderer
# ===========================================
def _render_led_painter(
    small_frame: np.ndarray,
    out_h: int, out_w: int,
    scale: int, radius: float,
    bg_color: Tuple[int, int, int],
) -> np.ndarray:
    """
    Draw overlapping LED circles using the PAINTER'S ALGORITHM.

    WHAT IS THE PAINTER'S ALGORITHM?
    Imagine painting a canvas: each brush stroke covers whatever came before.
    We draw each LED circle one at a time, left-to-right, top-to-bottom.
    Where two adjacent circles overlap, the LATER one wins — it paints over
    the earlier one. Simple and fast, but the result depends on draw order.

    WHY math.ceil FOR THE RADIUS?
    The geometric radius for corner-touch circles is 5√2 ≈ 7.071, which is
    not a whole number. cv2.circle needs an integer. If we use round() we get 7,
    which is just short of 7.071 — leaving tiny black dots at the corner
    intersections. math.ceil gives 8, which always covers those pixels.
    """
    h, w = small_frame.shape[:2]
    output = np.empty((out_h, out_w, 3), dtype=np.uint8)
    output[...] = bg_color
    r_int = math.ceil(radius)
    for row in range(h):
        for col in range(w):
            cx = col * scale + scale // 2
            cy = row * scale + scale // 2
            color = tuple(int(v) for v in small_frame[row, col])
            cv2.circle(output, (cx, cy), r_int, color, thickness=-1)
    return output


# Cache for the distance grid used by circle modes.
# The grid only depends on the output size and scale, not the frame content,
# so we compute it once and reuse it every frame (much faster!).
_preview_dist_cache: dict = {}


def _render_led_gaussian(
    small_frame: np.ndarray,
    out_h: int,
    out_w: int,
    scale: int,
    sigma: float,
) -> np.ndarray:
    """
    Gaussian diffuser simulation.

    HOW IT WORKS:
    ==============
    A real LED matrix with a diffuser panel in front looks like soft glowing
    dots, not hard circles. This mode simulates that appearance by treating
    each LED as a POINT SOURCE of light and then blurring it with a Gaussian
    kernel — just like a physical diffuser spreads light from a point source.

    STEPS:
    1. Create a black image the same size as the output
    2. Place each LED's colour as a single bright pixel at its cell centre
    3. Apply Gaussian blur — each pixel spreads into a soft glow
    4. Normalise brightness back to the original level (the blur dims the peaks)

    WHY THIS SIGMA VALUE?
    Using a photo of a real LED matrix with diffuser panel, we measured:
    - Gap-to-peak brightness ratio:  ~37%
    - FWHM (full-width at half-max):  ~63% of cell pitch
    With sigma = scale × 0.27, our simulation predicts gap/peak ≈ 36% — a
    near-perfect match to the measured hardware.

    PARAMETERS:
    - sigma: controls how far the light spreads (larger = softer, more blurred)
    - peak_factor: restores the peak brightness (maths: 2π × σ² for a 2D Gaussian)
    """
    h, w = small_frame.shape[:2]

    # Step 1: create black canvas, place one bright pixel per LED at its centre
    dots = np.zeros((out_h, out_w, 3), dtype=np.float32)
    for row in range(h):
        for col in range(w):
            cy = row * scale + scale // 2   # Y coordinate of this LED's centre
            cx = col * scale + scale // 2   # X coordinate of this LED's centre
            dots[cy, cx] = small_frame[row, col].astype(np.float32)

    # Step 2: spread each point source with Gaussian blur
    # cv2.GaussianBlur with ksize=(0,0) auto-sizes the kernel from sigma
    blurred = cv2.GaussianBlur(dots, (0, 0), sigma)

    # Step 3: normalise — restore peak brightness (2π σ² is the 2D Gaussian area)
    peak_factor = 2.0 * math.pi * sigma * sigma
    return np.clip(blurred * peak_factor, 0, 255).astype(np.uint8)


def render_led_preview(
    small_frame: np.ndarray,
    algorithm: RenderAlgorithm = RenderAlgorithm.SQUARES,
    led_size_pct: int = 100,
    scale: int = 10,
    bg_color: Tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    """
    Render the 64x32 LED frame as a larger image simulating the LED matrix.

    WHAT'S HAPPENING:
    ==================
    The LED matrix has 64x32 tiny LEDs arranged in a grid.
    This function upscales that tiny image so we can see it on screen.

    RENDER ALGORITHMS:
    - SQUARES:           Plain 10x10 squares — simple, fast
    - CIRCLES:           Hard-edged circles; led_size_pct controls diameter
    - GAUSSIAN_RAW:      Gaussian blur (σ≈18% cell, no diffuser)
    - GAUSSIAN_DIFFUSED: Gaussian blur (σ≈27% cell, with diffuser panel)

    HOW THE SCALE WORKS:
    Each LED pixel becomes a scale×scale block in the output.
    With scale=10: 64×32 becomes 640×320 pixels.

    RETURNS:
    - A larger image (scale × bigger) ready for the preview window
    """
    h, w = small_frame.shape[:2]
    out_h, out_w = h * scale, w * scale

    # ===== SQUARES (simple nearest-neighbour upscale) =====
    if algorithm == RenderAlgorithm.SQUARES:
        return cv2.resize(small_frame, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    # ===== GAUSSIAN RAW — no diffuser panel =====
    if algorithm == RenderAlgorithm.GAUSSIAN_RAW:
        sigma = scale * 0.18  # σ ≈ 18% of cell — calibrated to raw hardware
        return _render_led_gaussian(small_frame, out_h, out_w, scale, sigma)

    # ===== GAUSSIAN DIFFUSED — with diffuser panel =====
    if algorithm == RenderAlgorithm.GAUSSIAN_DIFFUSED:
        sigma = scale * 0.27  # σ ≈ 27% of cell — calibrated with diffuser
        return _render_led_gaussian(small_frame, out_h, out_w, scale, sigma)

    # ===== CIRCLES — compute radius from led_size_pct =====
    half = scale / 2.0
    radius = scale * (led_size_pct / 200.0)

    # Overlapping circles (radius > half-cell) use painter's algorithm
    if radius > half:
        return _render_led_painter(small_frame, out_h, out_w, scale, radius, bg_color)

    # Non-overlapping circles — fast vectorised NumPy mask
    colored = cv2.resize(small_frame, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    cache_key = (out_h, out_w, scale)
    if cache_key not in _preview_dist_cache:
        xs = (np.arange(out_w) % scale - scale // 2).astype(np.float32)
        ys = (np.arange(out_h) % scale - scale // 2).astype(np.float32)
        dx, dy = np.meshgrid(xs, ys)
        _preview_dist_cache[cache_key] = np.sqrt(dx ** 2 + dy ** 2)

    dist = _preview_dist_cache[cache_key]
    mask = dist <= radius

    bg = np.empty((out_h, out_w, 3), dtype=np.uint8)
    bg[...] = bg_color

    return np.where(mask[:, :, np.newaxis], colored, bg).astype(np.uint8)


# ===========================================
# FUNCTION: Show preview windows
# ===========================================
def show_preview(original_frame: np.ndarray, small_frame: np.ndarray, orient: str = 'landscape', enabled: bool = True, proc_mode: str = 'center', algorithm: RenderAlgorithm = RenderAlgorithm.SQUARES, led_size_pct: int = 100) -> None:
    """
    Display a side-by-side preview: camera feed on the left, enlarged matrix
    view on the right.

    A blue rectangle on the camera side shows exactly which region of the camera
    frame is sent to the matrix portal.  For center-crop mode this is an inner
    crop rectangle; for stretch/fit it frames the whole camera image.

    In portrait mode the matrix view is rotated 90° CCW to match the physical
    display orientation.

    NOTE: On a headless Raspberry Pi (no monitor), keep SHOW_PREVIEW = False!
    """
    if not enabled:
        return

    # Enlarge the matrix view using the selected LED render algorithm
    enlarged = render_led_preview(small_frame, algorithm, led_size_pct, scale=10, bg_color=(0, 0, 0))

    # In portrait mode, rotate the matrix view to match the physical display
    if orient == 'portrait':
        enlarged = cv2.rotate(enlarged, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # Scale camera frame to match the enlarged matrix view height
    target_height = enlarged.shape[0]
    cam_h, cam_w = original_frame.shape[:2]
    cam_resized = cv2.resize(original_frame, (int(cam_w * target_height / cam_h), target_height))

    # Draw blue border showing the region sent to the matrix portal
    if proc_mode == 'center':
        # Target dims before rotation (portrait swaps w/h before cropping)
        tw = MATRIX_HEIGHT if orient == 'portrait' else MATRIX_WIDTH
        th = MATRIX_WIDTH if orient == 'portrait' else MATRIX_HEIGHT
        target_aspect = tw / th
        cam_aspect = cam_w / cam_h
        if cam_aspect > target_aspect:
            crop_w = int(cam_h * target_aspect)
            x1, y1 = (cam_w - crop_w) // 2, 0
            x2, y2 = x1 + crop_w, cam_h
        else:
            crop_h = int(cam_w / target_aspect)
            x1, y1 = 0, (cam_h - crop_h) // 2
            x2, y2 = cam_w, y1 + crop_h
    else:
        # stretch / fit — full camera frame is used
        x1, y1, x2, y2 = 0, 0, cam_w, cam_h

    # Scale crop rect from original camera coordinates to preview coordinates
    s = target_height / cam_h
    px1, py1 = int(x1 * s), int(y1 * s)
    px2, py2 = min(int(x2 * s), cam_resized.shape[1]) - 1, int(y2 * s) - 1
    cv2.rectangle(cam_resized, (px1, py1), (px2, py2), (255, 0, 0), 1)

    # Show both views side by side in a single window
    # cv2.waitKey(1) is required to actually render the frame — without it imshow
    # queues the image but the window never updates (critical during countdown).
    combined = np.hstack([cam_resized, enlarged])
    cv2.imshow("Camera | LED Matrix (10x)", combined)
    cv2.waitKey(1)


# ===========================================
# FUNCTION: Print help
# ===========================================
def print_help(orient: str, proc_mode: str, bw: bool, mirror: bool, algorithm: RenderAlgorithm, led_size_pct: int, debug: bool) -> None:
    """Print the help message with current settings."""
    print("")
    print("=" * 60)
    print("KEYBOARD COMMANDS:")
    print("  Orientation: l=landscape  p=portrait")
    print("  Processing:  c=center  s=stretch  f=fit")
    print("  Effects:     b=B&W toggle  m=mirror toggle  o=render algorithm")
    print("  LED size:    +/= increase  -/_ decrease (Circles only)")
    print("  Actions:     SPACE=snapshot  v=avatar")
    print("  System:      t=toggle transmission  w=preview  d=debug  r=reset  h=help  q=quit")
    print("")
    bw_str = "B&W" if bw else "Color"
    mirror_str = "Mirrored" if mirror else "Normal"
    algo_str = algorithm.name.lower().replace('_', ' ')
    debug_str = "ON" if debug else "OFF"
    print(f"  Current: {orient.title()} + {proc_mode.title()}, {bw_str}, Mirror={mirror_str}, Algorithm={algo_str}, Size={led_size_pct}%, Debug={debug_str}")
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
    global orientation, processing_mode, black_and_white_mode, mirror_mode, render_algorithm, led_size_pct, debug_output
    show_preview_enabled = SHOW_PREVIEW  # Local toggle; SHOW_PREVIEW sets the startup default

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="LED Matrix Camera Feed")
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable debug/stats output (toggle with 'd' key)",
    )
    args = parser.parse_args()
    if args.no_debug:
        debug_output = False

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

    # Detect and list all available cameras
    print("=" * 50)
    print("DETECTING CAMERAS")
    print("=" * 50)
    available_cameras = list_available_cameras()
    if available_cameras:
        print(f"Found {len(available_cameras)} camera(s):")
        for cam in available_cameras:
            index = cam.get('index', '?')
            cam_type = cam.get('type', 'unknown')
            backend = cam.get('backend', 'unknown')
            resolution = cam.get('resolution', 'unknown')
            fps = cam.get('fps', 'unknown')
            model = cam.get('model', '')
            model_str = f" - {model}" if model else ""
            print(f"  [{index}] {cam_type} ({backend}){model_str}")
            print(f"       Resolution: {resolution}, FPS: {fps}")
    else:
        print("  No cameras detected")
    print("")

    # Set up camera (tries Pi Camera first, then USB)
    print("=" * 50)
    print("OPENING CAMERA")
    print("=" * 50)
    camera, camera_type = setup_camera()
    print(f"  Camera type: {camera_type}")

    # Display camera details
    if camera_type == "opencv":
        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = camera.get(cv2.CAP_PROP_FPS)
        backend = camera.getBackendName()
        print(f"  Backend: {backend}")
        print(f"  Resolution: {width}x{height}")
        print(f"  FPS (reported by driver): {fps if fps > 0 else 'unknown'} — camera driver reported speed.")
    elif camera_type == "picamera":
        camera_props = camera.camera_properties
        config = camera.camera_configuration()
        main_stream = config.get("main", {})
        size = main_stream.get("size", (0, 0))
        model = camera_props.get("Model", "Unknown")
        print(f"  Model: {model}")
        print(f"  Resolution: {size[0]}x{size[1]}")
        print(f"  Sensor modes: {len(camera.sensor_modes)}")
    print("")

    # Connect to LED matrix
    serial_connection = setup_usb_serial()

    if serial_connection is None:
        print("\nWARNING: LED Matrix not connected!")
        print("Display paused (device not found). Press 't' to retry.")

    print("")
    print("=" * 50)
    print("STEP 3: Starting the camera feed!")
    print("=" * 50)
    print("")
    print_help(orientation, processing_mode, black_and_white_mode, mirror_mode, render_algorithm, led_size_pct, debug_output)
    if show_preview_enabled:
        print("Preview window: ENABLED (press 'w' to toggle)")
    print("Press Ctrl+C to force quit")
    if serial_connection is None:
        print("\n!!! Matrix Portal not connected — press 't' to connect when ready. !!!\n")
    print("")

    frame_count = 0
    start_time = time.time()
    display_enabled = True  # User's intent to send to display
    display_status = "unknown"  # Current display status with reason
    last_sent_frame = None  # Last frame successfully delivered to the device

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

            if key == 'm':
                mirror_mode = not mirror_mode
                mode_str = "ON" if mirror_mode else "OFF"
                print(f"\n=== MIRROR: {mode_str} ===\n")
                continue

            if key == 'o':
                next_val = (render_algorithm.value + 1) % len(RenderAlgorithm)
                render_algorithm = RenderAlgorithm(next_val)
                print(f"\n=== RENDER ALGORITHM: {ALGORITHM_LABELS[render_algorithm]} ===\n")
                continue

            if key in ('+', '='):
                if render_algorithm == RenderAlgorithm.CIRCLES:
                    idx = LED_SIZE_STEPS.index(led_size_pct) if led_size_pct in LED_SIZE_STEPS else -1
                    if idx < len(LED_SIZE_STEPS) - 1:
                        led_size_pct = LED_SIZE_STEPS[idx + 1]
                    print(f"\n=== LED SIZE: {led_size_pct}% ===\n")
                else:
                    print(f"\n=== LED SIZE: press 'o' to switch to Circles mode ===\n")
                continue

            if key in ('-', '_'):
                if render_algorithm == RenderAlgorithm.CIRCLES:
                    idx = LED_SIZE_STEPS.index(led_size_pct) if led_size_pct in LED_SIZE_STEPS else -1
                    if idx > 0:
                        led_size_pct = LED_SIZE_STEPS[idx - 1]
                    print(f"\n=== LED SIZE: {led_size_pct}% ===\n")
                else:
                    print(f"\n=== LED SIZE: press 'o' to switch to Circles mode ===\n")
                continue

            # === SYSTEM KEYS ===
            if key == 't':
                if display_enabled and serial_connection is None:
                    # Already enabled but disconnected — reconnect without toggling to paused
                    print("\n=== RECONNECTING TO MATRIX PORTAL ===")
                    serial_connection = setup_usb_serial()
                    if serial_connection is None:
                        print("Connection failed: Matrix Portal not found")
                        print("!!! Press 't' to try again when the portal is connected. !!!\n")
                    else:
                        print("Connected successfully!\n")
                else:
                    display_enabled = not display_enabled
                    if display_enabled:
                        print("\n=== DISPLAY: ENABLED ===")
                        if serial_connection is None:
                            print("Attempting to reconnect to Matrix Portal...")
                            serial_connection = setup_usb_serial()
                            if serial_connection is None:
                                print("Connection failed: Matrix Portal not found")
                                print("!!! Press 't' to try again when the portal is connected. !!!\n")
                            else:
                                print("Connected successfully!\n")
                        else:
                            print()
                    else:
                        print("\n=== DISPLAY: PAUSED (by user) — press 't' to resume ===\n")
                continue

            # === RESET ===
            if key == 'r':
                orientation = 'landscape'
                processing_mode = 'center'
                black_and_white_mode = False
                mirror_mode = False
                render_algorithm = RenderAlgorithm.SQUARES
                led_size_pct = 100
                debug_output = True
                display_enabled = True
                print("\n=== RESET TO DEFAULTS ===")
                print("Orientation=landscape, Processing=center, Color, Mirror=OFF, Algorithm=squares, Size=100%, Debug=ON, Display=ON\n")
                continue

            # === ACTION KEYS ===
            if key == 'd':
                debug_output = not debug_output
                status = "ON" if debug_output else "OFF"
                print(f"\n=== DEBUG: {status} ===\n")
                continue

            if key == 'w':
                show_preview_enabled = not show_preview_enabled
                if show_preview_enabled:
                    print("\n=== PREVIEW WINDOW: ENABLED ===\n")
                else:
                    cv2.destroyAllWindows()
                    cv2.waitKey(1)
                    print("\n=== PREVIEW WINDOW: DISABLED ===\n")
                continue

            if key == 'h':
                print_help(orientation, processing_mode, black_and_white_mode, mirror_mode, render_algorithm, led_size_pct, debug_output)
                continue

            if key == 'q':
                print("\n=== QUIT ===\n")
                break

            if key == ' ':
                if not display_enabled and last_sent_frame is not None:
                    # Paused: save the frozen frame that's on the device — no countdown
                    print("  Saving paused frame...")
                    frame_bytes_save = convert_to_rgb565(last_sent_frame)
                    save_snapshot(last_sent_frame, frame_bytes_save, orientation, debug_output)
                    speak("Saved")
                else:
                    run_snapshot(camera, camera_type, serial_connection, orientation, processing_mode, black_and_white_mode, mirror_mode, show_preview_enabled, render_algorithm, led_size_pct)
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
                continue

            # Process the frame
            small_frame = resize_frame(frame, orientation, processing_mode)

            if mirror_mode:
                small_frame = apply_mirror(small_frame)

            if black_and_white_mode:
                small_frame = apply_black_and_white(small_frame)

            # Apply brightness limit (set MAX_BRIGHTNESS in config.py)
            if MAX_BRIGHTNESS < 255:
                small_frame = np.minimum(small_frame, MAX_BRIGHTNESS).astype(np.uint8)

            # Convert and send
            frame_bytes = convert_to_rgb565(small_frame)
            bytes_sent = 0

            # Determine display status and send if enabled
            if not display_enabled:
                display_status = "PAUSED (user)"
            elif serial_connection is None:
                display_status = "PAUSED (no device)"
            else:
                try:
                    bytes_sent = send_frame(serial_connection, frame_bytes)
                    display_status = "ACTIVE"
                    last_sent_frame = small_frame  # Cache for pause-mode snapshot
                except Exception as e:
                    serial_connection = None  # Mark as disconnected so 't' can reconnect
                    display_status = "PAUSED (disconnected)"
                    print(f"Display disconnected: {e}")
                    print("\n!!! Matrix Portal disconnected — plug in and press 't' to reconnect. !!!\n")

            # Show preview
            show_preview(frame, small_frame, orientation, show_preview_enabled, processing_mode, render_algorithm, led_size_pct)

            # Statistics
            frame_count += 1
            if debug_output and frame_count % 10 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                mode_str = f"[{orientation[0].upper()}{processing_mode[0].upper()}]"
                bw_str = " [B&W]" if black_and_white_mode else ""
                display_info = f", Display: {display_status}" if display_status != "ACTIVE" else ""
                print(f"  Frames: {frame_count}, FPS: {fps:.1f}, Bytes: {bytes_sent}{mode_str}{bw_str}{display_info}")

            # Check for quit in preview window
            if show_preview_enabled:
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
        if show_preview_enabled:
            cv2.destroyAllWindows()
        print("Goodbye!")


# ===========================================
# RUN THE PROGRAM
# ===========================================
if __name__ == "__main__":
    main()
