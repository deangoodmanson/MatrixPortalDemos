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
| **`macropad/`** | **MacroPad Remote** | CircuitPython macro pages for the Adafruit MacroPad RP2040. Physical button controller for all camera feed commands. |

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
*   **Orientation**: `l` landscape (default) · `p` portrait
*   **Processing**: `c` center crop (default) · `s` stretch · `f` fit (letterbox)
*   **Effects**: `b` B&W toggle · `z` zoom (100% → 75% → 50% → 25%)
*   **Actions**: `Space` snapshot · `v` avatar capture
*   **System**: `t` toggle transmission · `r` reset · `d` debug · `h` help · `q` quit

## Performance Optimizations
We achieved a ~500% performance increase (5 FPS → 24 FPS) by:
1.  **Firmware**: Replaced Python pixel loops with `bitmaptools.arrayblit` (C-level memory copy).
2.  **Transport**: Increased USB Serial baud rate to **4,000,000**.
3.  **Pipeline**: Optimized frame resizing and RGB565 conversion in Python.

## Diagnostics

### RGB565 color artifact comparison

If the physical LED matrix shows color artifacts (wrong-colored pixels) that
do not appear in the software BMP snapshot, use the comparison script to
investigate:

```bash
cd MatrixPortalDemos
uv run --project pro python docs/compare_rgb565.py [pro/snapshot_*.bmp]
```

This produces a side-by-side 10× PNG (saved next to the BMP):

| Panel | Content |
|-------|---------|
| Left  | Original BMP — what the software saved / preview shows |
| Centre | After RGB565 roundtrip — what the matrix actually receives |
| Right | \|difference\| × 4 — artifact map |

The script also prints per-pixel and per-channel shift statistics.  A max
shift of ≤7 counts rules out RGB565 quantization as the cause.

See `docs/compare_rgb565.py` for the full methodology, RGB565 bit-layout
reference, and a guide to distinguishing rolling-shutter artifacts, camera
bloom, hardware LED variation, and serial bit flips.

## Troubleshooting

**"Matrix Portal not found"**
*   Check your USB cable (some are power-only!).
*   Ensure `code.py` is running on the device (screen should say "WAITING FOR USB").

**"Permission denied" (Linux/Pi)**
*   You may need to add your user to the `dialout` group: `sudo usermod -a -G dialout $USER`.
