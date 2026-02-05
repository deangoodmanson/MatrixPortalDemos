# LED Portal Code Versions Plan

This document outlines two potential versions of the LED Portal codebase, each optimized for different audiences and use cases.

---

## Version 1: High School Python Learning Class

**Goal:** Maximize learning, readability, and understanding of core concepts.

### 1.1 Extensive Comments

- Explain every block of code with "why" not just "what"
- Add comments explaining Python concepts (loops, functions, imports)
- Include ASCII diagrams showing data flow
- Example:
  ```python
  # A "for loop" repeats code a set number of times
  # Here we loop through each row (y) of the image
  for y in range(32):  # 32 rows, numbered 0-31
      for x in range(64):  # 64 columns per row
          # Process one pixel at position (x, y)
  ```

### 1.2 Simplified Structure

- Single file per component (no config imports)
- Inline all constants with explanations
- Remove argparse - use simple hardcoded values
- Remove advanced features (snapshot, countdown) initially

### 1.3 Educational Additions

- Add `print()` statements showing intermediate values
- Include "Try This!" comments suggesting experiments
- Add numbered sections matching a lesson plan
- Include common error explanations in comments
- Example:
  ```python
  # Try This! Change 64 to 32 and see what happens to the image
  MATRIX_WIDTH = 64

  # Common Error: If you see "cannot open camera", make sure
  # no other program (like Zoom) is using the webcam
  ```

### 1.4 Concept Isolation

Separate scripts for each concept, building up to the full system:

| Script | Concept | Learning Outcome |
|--------|---------|------------------|
| `01_camera_capture.py` | Camera basics | How to get images from a webcam |
| `02_image_resize.py` | OpenCV resize | Array manipulation, interpolation |
| `03_color_conversion.py` | RGB565 math | Binary, bit shifting, color representation |
| `04_serial_communication.py` | USB basics | How computers talk to devices |
| `05_full_system.py` | Combined version | Putting it all together |

### 1.5 Remove Complexity

- No error handling (let errors teach)
- No flow control options
- No test patterns
- Fixed baud rate with explanation
- No command-line arguments

### 1.6 Sample Lesson Plan Integration

```
Lesson 1: Digital Images (01_camera_capture.py)
  - What is a pixel?
  - How are images stored in memory?
  - Hands-on: Capture and display a frame

Lesson 2: Image Processing (02_image_resize.py)
  - Why resize images?
  - What is interpolation?
  - Hands-on: Resize to different dimensions

Lesson 3: Color Theory (03_color_conversion.py)
  - RGB color model
  - Why 16-bit color? (memory constraints)
  - Binary and bit shifting
  - Hands-on: Convert colors manually

Lesson 4: Hardware Communication (04_serial_communication.py)
  - What is serial communication?
  - Baud rate and protocols
  - Hands-on: Send data to the LED matrix

Lesson 5: Integration (05_full_system.py)
  - Combining components
  - Frame rate and timing
  - Hands-on: Build the complete system
```

---

## Version 2: Professional Software Engineering

**Goal:** Maintainability, testability, extensibility, team collaboration.

### 2.1 Project Structure

```
ledportal/
├── src/
│   ├── __init__.py
│   ├── capture/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract camera interface
│   │   ├── opencv_camera.py     # OpenCV implementation
│   │   └── picamera.py          # Raspberry Pi camera implementation
│   ├── transport/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract transport interface
│   │   └── serial_transport.py  # USB serial implementation
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── resize.py            # Image resizing utilities
│   │   └── color_convert.py     # RGB565/RGB332 conversion
│   └── ui/
│       ├── __init__.py
│       ├── snapshot.py          # Snapshot feature
│       └── overlay.py           # Countdown overlay
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_capture.py
│   ├── test_transport.py
│   ├── test_processing.py
│   └── test_integration.py
├── config/
│   ├── default.yaml             # Default configuration
│   ├── production.yaml          # Production overrides
│   └── development.yaml         # Development settings
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── adr/                     # Architecture Decision Records
│       └── 001-color-format.md
├── scripts/
│   └── setup_udev.sh            # Linux USB permissions
├── main.py                      # Application entry point
├── pyproject.toml               # Project metadata and dependencies
├── Makefile                     # Common commands
└── README.md
```

### 2.2 Abstraction & Interfaces

**Abstract Base Classes:**
```python
# src/capture/base.py
from abc import ABC, abstractmethod
from numpy import ndarray

class CameraInterface(ABC):
    @abstractmethod
    def capture(self) -> ndarray | None:
        """Capture a single frame."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release camera resources."""
        pass
```

**Design Patterns:**
- **Strategy Pattern:** For color conversion formats (RGB565, RGB332)
- **Factory Pattern:** For camera selection based on platform
- **Dependency Injection:** For testability

### 2.3 Configuration Management

**Layered Configuration:**
1. Default values in code
2. Configuration file (YAML)
3. Environment variables
4. Command-line arguments

**Example config/default.yaml:**
```yaml
matrix:
  width: 64
  height: 32

camera:
  width: 640
  height: 480
  index: 0

transport:
  baud_rate: 2000000
  timeout: 0.1
  write_timeout: 0.5

features:
  frame_limiting: false
  target_fps: 5
  countdown_duration: 0.5
```

**Validation with Pydantic:**
```python
from pydantic import BaseModel, validator

class MatrixConfig(BaseModel):
    width: int = 64
    height: int = 32

    @validator('width', 'height')
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('must be positive')
        return v
```

### 2.4 Error Handling

**Custom Exception Hierarchy:**
```python
class LEDPortalError(Exception):
    """Base exception for LED Portal."""
    pass

class CameraError(LEDPortalError):
    """Camera-related errors."""
    pass

class TransportError(LEDPortalError):
    """Communication errors."""
    pass

class ConfigurationError(LEDPortalError):
    """Invalid configuration."""
    pass
```

**Retry Logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def connect_serial(port: str, baud_rate: int) -> Serial:
    """Connect to serial port with retry."""
    return Serial(port, baudrate=baud_rate)
```

### 2.5 Testing Strategy

**Unit Tests:**
```python
# tests/test_processing.py
import pytest
import numpy as np
from src.processing.color_convert import convert_to_rgb565

def test_convert_red_pixel():
    """Pure red should convert to 0xF800 in RGB565."""
    frame = np.array([[[0, 0, 255]]], dtype=np.uint8)  # BGR red
    result = convert_to_rgb565(frame)
    assert result == b'\x00\xf8'

def test_convert_preserves_shape():
    """Output size should be width * height * 2 bytes."""
    frame = np.zeros((32, 64, 3), dtype=np.uint8)
    result = convert_to_rgb565(frame)
    assert len(result) == 32 * 64 * 2
```

**Mock Fixtures:**
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_camera():
    """Mock camera that returns test frames."""
    camera = Mock()
    camera.capture.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    return camera

@pytest.fixture
def mock_serial():
    """Mock serial port for testing transport."""
    serial = Mock()
    serial.is_open = True
    serial.write.return_value = 4096
    return serial
```

### 2.6 Logging & Observability

**Structured Logging:**
```python
import logging
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Usage
logger.info("frame_sent",
    frame_count=100,
    fps=4.8,
    bytes_sent=4096,
    latency_ms=12.5
)
```

**Metrics Collection:**
```python
from dataclasses import dataclass
from time import time

@dataclass
class FrameMetrics:
    capture_time_ms: float
    process_time_ms: float
    send_time_ms: float
    total_time_ms: float

class MetricsCollector:
    def __init__(self):
        self.frames: list[FrameMetrics] = []

    def report(self) -> dict:
        return {
            "avg_fps": len(self.frames) / sum(f.total_time_ms for f in self.frames) * 1000,
            "avg_latency_ms": sum(f.total_time_ms for f in self.frames) / len(self.frames)
        }
```

### 2.7 Documentation Standards

**Docstrings (Google Style):**
```python
def convert_to_rgb565(frame: np.ndarray) -> bytes:
    """Convert BGR frame to RGB565 format.

    Args:
        frame: Input frame in BGR format, shape (height, width, 3).

    Returns:
        Bytes array in RGB565 little-endian format,
        length = height * width * 2.

    Raises:
        ValueError: If frame doesn't have 3 channels.

    Example:
        >>> frame = np.zeros((32, 64, 3), dtype=np.uint8)
        >>> data = convert_to_rgb565(frame)
        >>> len(data)
        4096
    """
```

**Type Hints:**
```python
from typing import Optional, Tuple
from numpy import ndarray

def setup_camera(index: int = 0) -> Tuple[object, str]:
    ...

def capture_frame(camera: object, camera_type: str) -> Optional[ndarray]:
    ...
```

---

## Key Differences Summary

| Aspect | High School | Professional |
|--------|-------------|--------------|
| **Files** | 5 single-purpose scripts | 15+ modular files |
| **Comments** | Verbose, educational | Minimal, self-documenting |
| **Config** | Hardcoded constants | External YAML + env vars |
| **Errors** | Let them happen (learning) | Handle gracefully + retry |
| **Testing** | Manual only | Automated pytest suite |
| **Types** | None | Full type hints |
| **Logging** | print() statements | Structured JSON logging |
| **Dependencies** | Minimal, pip install | pyproject.toml, locked versions |
| **Audience** | Individual learner | Development team |
| **Goal** | Understanding | Maintainability |

---

## Implementation Notes

### For High School Version
- Start with `01_camera_capture.py` and build up
- Each script should be runnable independently
- Include expected output in comments
- Provide a "solutions" folder for completed exercises

---

## Additional High School-Friendly Enhancements

### Simplify Variable Names
```python
# Instead of:
rgb565 = (r << 11) | (g << 5) | b

# Use:
red_part = red_bits * 2048      # Same as shifting left 11 bits
green_part = green_bits * 32    # Same as shifting left 5 bits
blue_part = blue_bits
combined_color = red_part + green_part + blue_part
```

### Add Visual Output
- Display the webcam feed in a window so students can see what's being captured
- Show the resized 64x32 image enlarged so it's visible
- Add a color swatch showing RGB565 vs original color

```python
# Show what the camera sees
cv2.imshow("Camera View", frame)

# Show the tiny matrix-sized image (enlarged 10x so you can see it)
big_preview = cv2.resize(small_frame, (640, 320), interpolation=cv2.INTER_NEAREST)
cv2.imshow("What the LED Matrix Sees", big_preview)
```

### Replace Bit Shifting with Math
```python
# BEFORE (confusing for beginners):
r = (rgb[:, :, 0] >> 3).astype(np.uint16)  # 5 bits

# AFTER (clearer):
# Divide by 8 to reduce 256 levels (0-255) down to 32 levels (0-31)
# This keeps only the 5 most important bits of color information
red_reduced = rgb[:, :, 0] // 8  # 256 colors -> 32 colors
```

### Add Progress Indicators
```python
print("Step 1 of 4: Capturing image from camera...")
frame = capture_frame(camera)
print("  Done! Image size:", frame.shape)

print("Step 2 of 4: Resizing image to 64x32...")
small = resize_frame(frame)
print("  Done! New size:", small.shape)

print("Step 3 of 4: Converting colors to RGB565...")
data = convert_to_rgb565(small)
print("  Done! Data size:", len(data), "bytes")

print("Step 4 of 4: Sending to LED matrix...")
send_frame(serial_port, data)
print("  Done! Frame displayed!")
```

### Include "What If?" Experiments
```python
# ===========================================
# EXPERIMENT 1: What happens with different sizes?
# ===========================================
# Try changing these numbers and see what happens!
# What if width is bigger than height?
# What if they're both really small like 8x8?

MATRIX_WIDTH = 64   # Try: 32, 16, 8
MATRIX_HEIGHT = 32  # Try: 16, 8, 4

# ===========================================
# EXPERIMENT 2: What if we skip the resize?
# ===========================================
# Uncomment the line below to send the full camera image
# (Hint: it won't fit and will look weird!)

# small_frame = frame  # Skip resize - what happens?
```

### Add Glossary Comments
```python
# GLOSSARY:
# ---------
# Pixel: One tiny dot of color in an image (like a single LED)
# Frame: One complete image/picture from the camera
# RGB: Red, Green, Blue - the three colors that combine to make any color
# Resolution: How many pixels wide and tall an image is (like 64x32)
# Baud rate: How fast data travels through the USB cable (bits per second)
# Serial: A way to send data one bit at a time through a cable
```

### Provide Fill-in-the-Blank Exercises
```python
# EXERCISE: Fill in the blanks!
#
# The LED matrix is ____ pixels wide and ____ pixels tall.
# Total pixels = ____ x ____ = ______ pixels
#
# Each pixel needs 2 bytes of color data.
# Total bytes per frame = ______ pixels x 2 = ______ bytes

MATRIX_WIDTH = ____   # Fill in: How wide is the matrix?
MATRIX_HEIGHT = ____  # Fill in: How tall is the matrix?
```

### Add Checkpoints with Expected Output
```python
# ========================================
# CHECKPOINT 1: Camera Working?
# ========================================
# When you run this, you should see:
#   "Camera opened successfully!"
#   "Frame captured! Size: (480, 640, 3)"
#
# If you see an error, check:
#   - Is another app using the camera?
#   - Is the webcam plugged in?
# ========================================

camera = cv2.VideoCapture(0)
if camera.isOpened():
    print("Camera opened successfully!")
else:
    print("ERROR: Could not open camera!")
    exit()

ret, frame = camera.read()
if ret:
    print("Frame captured! Size:", frame.shape)
else:
    print("ERROR: Could not capture frame!")
```

### Use Analogies in Comments
```python
# Think of RGB565 like packing a suitcase:
# - You have a BIG suitcase (24-bit color = 16 million colors)
# - You need to fit everything in a SMALL suitcase (16-bit = 65,536 colors)
# - You keep the most important clothes and leave behind the rest
#
# Original: Red has 256 shades (0-255)
# Packed:   Red has 32 shades (0-31) - we keep the 5 most important bits
```

### Create a "Debug Mode" Toggle
```python
# Set this to True to see extra information while the program runs
# Set to False for normal operation
DEBUG_MODE = True

if DEBUG_MODE:
    print(f"Camera frame size: {frame.shape}")
    print(f"Resized frame size: {small_frame.shape}")
    print(f"Bytes to send: {len(frame_bytes)}")
    print(f"First 10 bytes: {frame_bytes[:10]}")
```

### Include Real-World Context
```python
# ===========================================
# WHY RGB565?
# ===========================================
#
# Normal images use 24 bits per pixel (8 bits each for Red, Green, Blue)
# That's 16.7 MILLION possible colors!
#
# But our tiny LED matrix doesn't need that many colors, and sending
# that much data would be slow. So we use RGB565:
#   - 5 bits for Red   (32 shades)
#   - 6 bits for Green (64 shades) - humans see green better!
#   - 5 bits for Blue  (32 shades)
#   = 16 bits total = 65,536 colors
#
# This is the same color format used by:
#   - Old flip phones
#   - Nintendo Game Boy Advance
#   - Many small LCD screens
# ===========================================
```

### Provide Starter Templates
```python
#!/usr/bin/env python3
"""
MY LED MATRIX PROJECT
By: [Your Name Here]
Date: [Today's Date]

This program captures video from my webcam and displays it
on a 64x32 LED matrix!
"""

# ===========================================
# STEP 1: IMPORT THE TOOLS WE NEED
# ===========================================
# These are like importing LEGO pieces before building
import cv2      # For camera and image stuff
import serial   # For talking to the LED matrix

# ===========================================
# STEP 2: SET UP THE CAMERA
# ===========================================
# Your code here...

# ===========================================
# STEP 3: CAPTURE AND SEND FRAMES
# ===========================================
# Your code here...
```

### For Professional Version
- Use `cookiecutter` or similar for project scaffolding
- Set up pre-commit hooks (black, isort, mypy)
- Include CI/CD configuration (GitHub Actions)
- Add contribution guidelines (CONTRIBUTING.md)

---

## Current Codebase Status

The current codebase (`sandbox/camera_feed.py`, `pi/camera_feed.py`, `matrix-portal/code.py`) represents a **working prototype** that sits between these two versions:

- More complex than the educational version
- Less structured than the professional version
- Suitable for demonstration and personal use
- Good starting point for either direction

To create either version, the current code provides a solid functional reference that can be refactored accordingly.
