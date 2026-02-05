#!/usr/bin/env python3
"""
===========================================
LED MATRIX CAMERA FEED
High School Learning Version (macOS)
===========================================

This program captures video from your webcam and displays it
on a 64x32 LED matrix in real-time!

WHAT YOU'LL LEARN:
- How digital cameras capture images
- How images are stored as numbers (pixels)
- How to resize and crop images
- How colors work (RGB and RGB565)
- How to send data to hardware devices
- How to handle keyboard input
- How to use text-to-speech

FEATURES:
- Multiple display modes (crop, squish, letterbox, portrait)
- Black & white mode
- Snapshot with countdown
- Avatar capture mode with voice prompts

REQUIREMENTS:
- Python 3
- OpenCV (cv2) - for camera and image processing
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
import json                         # For saving data in JSON format
from datetime import datetime       # For timestamps

# ===========================================
# ADVANCED IMPORTS (Unix/Mac/Linux only)
# ===========================================
# These modules let us read single keypresses without waiting for Enter.
# This is an ADVANCED concept - normally input() waits for Enter.
#
# HOW IT WORKS:
# - 'tty' controls terminal behavior
# - 'termios' stores/restores terminal settings
# - We switch to "cbreak" mode where each keypress is sent immediately
#
# NOTE: This won't work on Windows! Windows uses a different system.

import tty
import termios

# ===========================================
# ADVANCED IMPORTS (Text-to-Speech)
# ===========================================
# These modules let us make the computer talk!
# - 'subprocess' runs external programs (like the 'say' command on Mac)
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
SHOW_PREVIEW = True

# The "magic word" we send before each frame so the LED matrix
# knows a new picture is coming (like saying "incoming!")
FRAME_HEADER = b'IMG1'

# How fast to send data (2 million bits per second!)
BAUD_RATE = 2000000

# How long to show each countdown number (in seconds)
COUNTDOWN_DURATION = 0.5

# ===========================================
# DISPLAY MODES
# ===========================================
# These control how the camera image is fit into the LED matrix.
# The matrix is 64 pixels wide and 32 pixels tall (2:1 ratio).
# Most cameras capture at 4:3 ratio (like 640x480).
# We need to decide: crop, stretch, or add black bars?

DISPLAY_MODES = ['landscape', 'portrait', 'squish', 'letterbox']

# Current settings (these can be changed with keyboard commands)
display_mode = 'landscape'      # How to fit the image
black_and_white_mode = False    # Color or grayscale?
debug_output = True             # Show frame rate info?

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
def setup_camera(camera_number=0):
    """
    Connect to the webcam and get it ready to take pictures.

    WHAT'S HAPPENING:
    - camera_number is which camera to use (0 = first camera)
    - We tell the camera what resolution we want
    - If it works, we get a "camera" object to take pictures with

    RETURNS:
    - A camera object we can use to capture frames
    """
    print("=" * 50)
    print("STEP 1: Setting up the camera")
    print("=" * 50)

    # Try to open the camera
    print(f"  Opening camera #{camera_number}...")
    camera = cv2.VideoCapture(camera_number)

    # Check if it worked
    if not camera.isOpened():
        print("  ERROR: Could not open the camera!")
        print("  ")
        print("  TROUBLESHOOTING:")
        print("  - Is another app using the camera (Zoom, FaceTime)?")
        print("  - Is the webcam plugged in?")
        print("  - Try changing camera_number to 1 or 2")
        raise RuntimeError("Failed to open camera")

    # Tell the camera what resolution we want
    print(f"  Setting resolution to {CAMERA_WIDTH}x{CAMERA_HEIGHT}...")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    print("  Camera is ready!")
    return camera


# ===========================================
# FUNCTION: Capture one picture
# ===========================================
def capture_frame(camera):
    """
    Take a single picture from the camera.

    WHAT'S HAPPENING:
    - We ask the camera to capture one frame (picture)
    - The camera returns the image as a big grid of numbers
    - Each pixel has 3 numbers: Blue, Green, Red (BGR)

    RETURNS:
    - A frame (image) as a numpy array, or None if it failed
    """
    # Read one frame from the camera
    success, frame = camera.read()

    if not success:
        # Something went wrong!
        return None

    return frame


# ===========================================
# FUNCTION: Resize the image with display modes
# ===========================================
def resize_frame(frame, mode='landscape'):
    """
    Resize and/or crop the camera image to fit the LED matrix.

    WHY WE NEED THIS:
    - Camera captures 640x480 = 307,200 pixels (4:3 ratio)
    - LED matrix only has 64x32 = 2,048 pixels (2:1 ratio)
    - The shapes don't match! We need to decide what to do.

    DISPLAY MODES:
    ==============

    LANDSCAPE (default):
    - Crops to 2:1 ratio from the CENTER of the image
    - Good for: normal horizontal display
    - You lose the top and bottom of the image

    PORTRAIT:
    - Crops to 1:2 ratio, then rotates 90 degrees
    - Good for: when the LED matrix is mounted vertically
    - You lose the left and right of the image

    SQUISH:
    - Stretches the entire image to fit
    - Nothing is cropped, but proportions are distorted
    - Good for: seeing everything (faces might look wide)

    LETTERBOX:
    - Shrinks to fit WITHOUT distortion
    - Adds black bars to fill empty space
    - Good for: no distortion, no cropping

    RETURNS:
    - A 64x32 pixel image ready for the LED matrix
    """
    height, width = frame.shape[:2]  # Get image dimensions

    # ===== LETTERBOX MODE =====
    if mode == 'letterbox':
        # Calculate how much to shrink to fit entirely
        scale_width = MATRIX_WIDTH / width
        scale_height = MATRIX_HEIGHT / height
        scale = min(scale_width, scale_height)  # Use the smaller scale

        # Calculate new size
        new_width = int(width * scale)
        new_height = int(height * scale)

        # Resize the image
        resized = cv2.resize(frame, (new_width, new_height))

        # Create a black canvas (all zeros = black)
        canvas = np.zeros((MATRIX_HEIGHT, MATRIX_WIDTH, 3), dtype=np.uint8)

        # Calculate where to put the image (centered)
        x_offset = (MATRIX_WIDTH - new_width) // 2
        y_offset = (MATRIX_HEIGHT - new_height) // 2

        # Place the resized image on the black canvas
        canvas[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = resized

        return canvas

    # ===== SQUISH MODE =====
    elif mode == 'squish':
        # Just resize directly - stretches to fit
        return cv2.resize(frame, (MATRIX_WIDTH, MATRIX_HEIGHT))

    # ===== PORTRAIT MODE =====
    elif mode == 'portrait':
        # For portrait, we want a tall narrow crop (1:2 ratio)
        target_width = height // 2  # Width should be half of height
        if target_width > width:
            target_width = width

        # Crop from the CENTER horizontally
        start_x = (width - target_width) // 2
        cropped = frame[0:height, start_x:start_x + target_width]

        # Resize to 32x64 (swapped dimensions)
        resized = cv2.resize(cropped, (MATRIX_HEIGHT, MATRIX_WIDTH))

        # Rotate 90 degrees clockwise
        rotated = cv2.rotate(resized, cv2.ROTATE_90_CLOCKWISE)

        return rotated

    # ===== LANDSCAPE MODE (default) =====
    else:
        # For landscape, we want a wide crop (2:1 ratio)
        target_height = width // 2  # Height should be half of width
        if target_height > height:
            target_height = height

        # Crop from the CENTER vertically
        start_y = (height - target_height) // 2
        cropped = frame[start_y:start_y + target_height, 0:width]

        # Resize to matrix dimensions
        return cv2.resize(cropped, (MATRIX_WIDTH, MATRIX_HEIGHT))


# ===========================================
# FUNCTION: Convert to black and white
# ===========================================
def apply_black_and_white(frame):
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
def convert_to_rgb565(frame):
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
def find_matrix_portal():
    """
    Search for the Matrix Portal device on USB.

    RETURNS:
    - The path to the serial port (like "/dev/cu.usbmodem1234")
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
def setup_usb_serial():
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
def send_frame(serial_connection, frame_bytes):
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
def check_keyboard():
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
def speak(text):
    """
    Make the computer speak using text-to-speech.

    ADVANCED CONCEPT: Running External Programs
    ===========================================
    Python can run other programs on your computer using subprocess.
    We use this to run the text-to-speech command.

    Different operating systems have different TTS commands:
    - macOS: 'say' command with fun voices like "Zarvox" (robot)
    - Linux: 'espeak-ng' with robotic settings
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

        elif system == "Linux":
            # espeak-ng with robotic settings
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
# FUNCTION: Save a snapshot
# ===========================================
def save_snapshot(frame, frame_bytes):
    """
    Save the current frame to disk.

    WHAT'S SAVED:
    - A .bmp image file (viewable in any image viewer)
    - A .bin file with raw RGB565 data (for the LED matrix)

    The filename includes a timestamp so each snapshot is unique.

    RETURNS:
    - The filename of the saved image
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save the image
    image_filename = f"snapshot_{timestamp}.bmp"
    cv2.imwrite(image_filename, frame)

    # Save the raw RGB565 data
    rgb565_filename = f"snapshot_{timestamp}_rgb565.bin"
    with open(rgb565_filename, 'wb') as f:
        f.write(frame_bytes)

    print(f"\n{'='*60}")
    print(f"SNAPSHOT SAVED:")
    print(f"  Color BMP: {image_filename}")
    print(f"  RGB565 data: {rgb565_filename}")
    print(f"{'='*60}\n")

    return image_filename


# ===========================================
# FUNCTION: Run snapshot countdown
# ===========================================
def run_snapshot(camera, serial_connection, current_mode, is_bw):
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
    print("\n=== SNAPSHOT MODE (SPACE or R to cancel) ===")
    speak("Get ready")

    # Countdown loop
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
            frame = capture_frame(camera)
            if frame is None:
                continue

            small_frame = resize_frame(frame, current_mode)
            if is_bw:
                small_frame = apply_black_and_white(small_frame)

            # Add countdown number to the frame
            overlay = small_frame.copy()
            cv2.putText(
                overlay,
                str(countdown),
                (2, MATRIX_HEIGHT - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),  # Red color (BGR)
                2
            )

            frame_bytes = convert_to_rgb565(overlay)
            send_frame(serial_connection, frame_bytes)

            time.sleep(0.01)

    # Take the actual snapshot
    print("  SNAP!")
    speak("Got it")

    frame = capture_frame(camera)
    if frame is not None:
        small_frame = resize_frame(frame, current_mode)
        if is_bw:
            small_frame = apply_black_and_white(small_frame)
        frame_bytes = convert_to_rgb565(small_frame)
        save_snapshot(small_frame, frame_bytes)
        send_frame(serial_connection, frame_bytes)

        # Pause to admire
        print("  Pausing for 5 seconds (SPACE or R to resume)...")
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
def run_avatar_capture(camera, serial_connection, current_mode):
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
            frame = capture_frame(camera)
            if frame is not None:
                small_frame = resize_frame(frame, current_mode)
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
                        print(f"  ✓ Captured!")
                        speak("Got it")
                        waiting = False
                    else:
                        speak("Failed, try again")

                elif key == 's':
                    skipped.append({"pose": pose_num, "angle": angle, "expression": expression})
                    print(f"  → Skipped")
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


def _save_manifest(avatar_dir, captured, skipped, session_time):
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
def show_preview(original_frame, small_frame):
    """
    Display preview windows so you can see what's happening.
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
def print_help(mode, bw, debug):
    """Print the help message with current settings."""
    print("")
    print("=" * 50)
    print("KEYBOARD COMMANDS:")
    print("  Display: C=crop  S=squish  L=letterbox  P=portrait")
    print("  Effects: B=B&W   N=normal(color)")
    print("  Actions: SPACE=snapshot  V=avatar  D=debug  R=reset  H=help  Q=quit")
    print("")
    bw_str = "B&W" if bw else "Color"
    debug_str = "ON" if debug else "OFF"
    print(f"  Current: Mode={mode}, {bw_str}, Debug={debug_str}")
    print("=" * 50)
    print("")


# ===========================================
# MAIN PROGRAM
# ===========================================
def main():
    """
    The main program that runs everything!

    ADVANCED CONCEPT: Terminal Modes
    ================================
    To read single keypresses (without Enter), we need to change
    how the terminal works. This is called "cbreak" mode.

    IMPORTANT: We MUST restore the terminal settings when we exit,
    or your terminal will be broken! That's why we use try/finally.
    """
    global display_mode, black_and_white_mode, debug_output

    # ===========================================
    # ADVANCED: Save and modify terminal settings
    # ===========================================
    # This lets us read single keypresses without Enter
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    print("")
    print("=" * 50)
    print("   LED MATRIX CAMERA FEED")
    print("   High School Learning Version")
    print("=" * 50)
    print("")
    print(f"Matrix size: {MATRIX_WIDTH} x {MATRIX_HEIGHT} pixels")
    print(f"Bytes per frame: {MATRIX_WIDTH * MATRIX_HEIGHT * 2}")
    print("")

    # Set up camera and connection
    camera = setup_camera()
    serial_connection = setup_usb_serial()

    if serial_connection is None:
        print("\nWARNING: LED Matrix not connected!")
        print("Running in preview-only mode...")

    print("")
    print("=" * 50)
    print("STEP 3: Starting the camera feed!")
    print("=" * 50)
    print("")
    print_help(display_mode, black_and_white_mode, debug_output)
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

            # === DISPLAY MODE KEYS ===
            if key == 'c':
                display_mode = 'landscape'
                print("\n=== MODE: LANDSCAPE (center crop) ===\n")
                continue

            if key == 's':
                display_mode = 'squish'
                print("\n=== MODE: SQUISH ===\n")
                continue

            if key == 'l':
                display_mode = 'letterbox'
                print("\n=== MODE: LETTERBOX ===\n")
                continue

            if key == 'p':
                display_mode = 'portrait'
                print("\n=== MODE: PORTRAIT ===\n")
                continue

            # === EFFECT KEYS ===
            if key == 'b':
                black_and_white_mode = True
                print("\n=== BLACK & WHITE MODE ===\n")
                continue

            if key == 'n':
                black_and_white_mode = False
                print("\n=== COLOR MODE ===\n")
                continue

            # === ACTION KEYS ===
            if key == 'd':
                debug_output = not debug_output
                status = "ON" if debug_output else "OFF"
                print(f"\n=== DEBUG: {status} ===\n")
                continue

            if key == 'r':
                display_mode = 'landscape'
                black_and_white_mode = False
                debug_output = True
                print("\n=== RESET TO DEFAULTS ===\n")
                continue

            if key == 'h':
                print_help(display_mode, black_and_white_mode, debug_output)
                continue

            if key == 'q':
                print("\n=== QUIT ===\n")
                break

            if key == ' ':
                run_snapshot(camera, serial_connection, display_mode, black_and_white_mode)
                # Clear any buffered input
                while select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)
                continue

            if key == 'v':
                run_avatar_capture(camera, serial_connection, display_mode)
                while select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)
                continue

            # === MAIN CAPTURE LOOP ===
            frame = capture_frame(camera)
            if frame is None:
                print("WARNING: Failed to capture frame")
                continue

            # Process the frame
            small_frame = resize_frame(frame, display_mode)

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
                mode_str = f"[{display_mode.upper()}]"
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
        camera.release()
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
