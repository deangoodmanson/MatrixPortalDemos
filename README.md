# LED Matrix Portal Camera Feed

Real-time high-performance camera feed displayed on a 64x32 RGB LED matrix.

## System Overview

```
Camera → Computer (Pi, Mac, PC) → USB Serial (4M baud) → Matrix Portal M4 → LED Matrix
```

- **Render Speed**: **~24 FPS** (Optimized from 5 FPS)
- **Tech Stack**: Python 3, CircuitPython 10, Optimized `bitmaptools`
- **Resolution**: 64x32 pixels, RGB565 color

## Project Versions

| Folder | Name | Description |
|--------|------|-------------|
| **`pro/`** | **Professional** | Modular, production-ready Python application. Uses `uv`, strict typing, and advanced config. |
| **`hs/`** | **High School** | Educational, single-folder version (`hs/src`) for students. Simplified code, cross-platform. |
| **`matrix-portal/`**| **Firmware** | CircuitPython code for the Adafruit Matrix Portal M4. |

## Raspberry Pi Workflows

### For Pro Version
**Best:** VS Code Remote SSH - develop on Mac, run on Pi hardware
```bash
# In VS Code: CMD+Shift+P → "Remote-SSH: Connect to Host"
# See pro/README.md for full setup
```

**Alternative:** Git clone + uv on Pi
```bash
git clone <repo>
cd pro
uv sync
uv run ledportal
```

### For HS Version (Educational)
**Simplest:** Direct file copy + Thonny editor
```bash
# No git, no build tools needed!
cd ~
mkdir ledportal-hs
wget <camera_feed.py>
pip3 install opencv-python pyserial numpy
python3 camera_feed.py
# Or open in Thonny IDE (pre-installed on Pi)
```

See `hs/README.md` and `pro/README.md` for detailed workflows.

## Quick Start

### 1. Setup Matrix Portal M4
Fastest way to get the display running:
1. Install CircuitPython 10.0.3+ on your Matrix Portal M4.
2. Installing required library: `circup install adafruit_display_text`
3. Copy `matrix-portal/code.py` to your `CIRCUITPY` drive.
4. Additional libraries needed in `lib/`: `adafruit_display_text`, `adafruit_matrixportal`.

### 2. Run the Camera Feed
You have two options to drive the display:

#### Option A: Professional (Recommended)
Fast, configurable, and robust.
```bash
cd pro
uv sync
uv run ledportal
```

#### Option B: Educational (Simple)
Great for learning how it works.
```bash
cd hs/src
# Create venv and install dependencies (opencv-python, pyserial, numpy)
uv venv && source .venv/bin/activate
uv pip install opencv-python numpy pyserial
python camera_feed.py
```

## Features
*   **Auto-Detection**: Code automatically finds the Matrix Portal USB device.
*   **Cross-Platform**: Works on macOS, Linux, Raspberry Pi, and Windows.
*   **Display Modes**:
    *   `l` - **Landscape** (Wide) (default)
    *   `p` - **Portrait** (Tall)
*   **Effects**:
    *   `c` - **Center** (Use the center of the camera image and clip the respected edges. Landscape: Top and Bottom, Portrait: Left and right) (default)
    *   `s` - **Stretch** (Stretch/Distort/Squish whole image on frame, Wide or Tall mode)
    *   `r` - **Resize to Fit** (Resized to Center, scale to Fit)
    *   `b` - **Toggle: Black and White & Color**    
*   **Tools**:
    *   `Space` - Take Snapshot (with countdown)
    *   `v` - Avatar Capture Mode (Guided session)
    *   `d` - **Toggle: Debug ouput on console**

## Performance Optimizations
We achieved a ~500% performance increase (5 FPS → 24 FPS) by:
1.  **Firmware**: Replaced Python pixel loops with `bitmaptools.arrayblit` (C-level memory copy).
2.  **Transport**: Increased USB Serial baud rate to **4,000,000**.
3.  **Pipeline**: Optimized frame resizing and RGB565 conversion in Python.

## Troubleshooting

**"Matrix Portal not found"**
*   Check your USB cable (some are power-only!).
*   Ensure `code.py` is running on the device (screen should say "WAITING FOR USB").

**"Permission denied" (Linux/Pi)**
*   You may need to add your user to the `dialout` group: `sudo usermod -a -G dialout $USER`.
