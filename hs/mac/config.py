"""
===========================================
CONFIGURATION SETTINGS
===========================================

This file contains all the settings for our LED Matrix project.
Change these values to experiment with different configurations!

GLOSSARY:
---------
- Resolution: How many pixels wide and tall (like 64x32)
- FPS: Frames Per Second - how many pictures we show each second
- Pixel: One tiny dot of color (like a single LED on the matrix)
"""

# ===========================================
# LED MATRIX SIZE
# ===========================================
# The LED matrix is like a tiny TV screen made of colored lights.
# Ours is 64 LEDs wide and 32 LEDs tall.
#
# EXPERIMENT: What happens if you change these numbers?
# (Hint: The image will look stretched or squished!)

MATRIX_WIDTH = 64    # How many LEDs across (left to right)
MATRIX_HEIGHT = 32   # How many LEDs down (top to bottom)

# Let's calculate some useful numbers:
TOTAL_PIXELS = MATRIX_WIDTH * MATRIX_HEIGHT  # = 2,048 pixels!
BYTES_PER_FRAME = TOTAL_PIXELS * 2           # = 4,096 bytes (2 bytes per pixel)

# ===========================================
# CAMERA SETTINGS
# ===========================================
# The webcam captures at a much higher resolution than we need.
# We'll shrink the image down to fit the LED matrix.

CAMERA_WIDTH = 640   # Webcam captures 640 pixels wide
CAMERA_HEIGHT = 480  # Webcam captures 480 pixels tall

# ===========================================
# SPEED SETTINGS
# ===========================================
# FPS = Frames Per Second
# Movies are usually 24 FPS, video games aim for 60 FPS
# Our little LED matrix works best at 5 FPS

TARGET_FPS = 5  # How many frames to display per second

# ===========================================
# PRINT A SUMMARY
# ===========================================
# This will show when the program starts so you know your settings

if __name__ == "__main__":
    print("=== LED Matrix Configuration ===")
    print(f"Matrix size: {MATRIX_WIDTH} x {MATRIX_HEIGHT} = {TOTAL_PIXELS} pixels")
    print(f"Bytes per frame: {BYTES_PER_FRAME}")
    print(f"Camera resolution: {CAMERA_WIDTH} x {CAMERA_HEIGHT}")
    print(f"Target FPS: {TARGET_FPS}")
