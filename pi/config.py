"""
Configuration settings for the camera feed.
"""

# LED Matrix dimensions
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 32

# Camera capture settings
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Target frame rate
TARGET_FPS = 10

# USB settings
# Using USB CDC serial - auto-detected by finding "CircuitPython" device
# The Matrix Portal exposes two serial ports: console and data
# We use the data port for frame transfers
