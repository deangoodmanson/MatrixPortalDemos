# LED Matrix Portal Camera Feed

Real-time camera feed displayed on a 64x32 RGB LED matrix.

## System Overview

```
Camera → Computer (Pi or Mac) → USB Serial → Matrix Portal M4 → LED Matrix
```

- **Raspberry Pi or Mac**: Captures and processes camera frames
- **Adafruit Matrix Portal M4**: Receives and displays frames at 5 FPS
- **Frame Format**: 64x32 pixels, RGB565 (16-bit color)

## Project Versions

| Folder | Description | Audience |
|--------|-------------|----------|
| `sandbox/` | Sandbox/playground - experimental features | Development |
| `pi/` | Synced copy of sandbox/ for Raspberry Pi | General use |
| `hs/` | High School learning version | Students learning Python |
| `pro/` | Professional modular version | Software engineers |
| `matrix-portal/` | CircuitPython receiver | LED matrix display |

## Quick Start

### 1. Setup Matrix Portal M4

```bash
# Install circup library manager
pip install circup

# Install required library
circup install adafruit_display_text
```

Follow instructions in `matrix-portal/README.md`:
- Install CircuitPython on Matrix Portal M4
- Copy `boot.py` and `code.py` to CIRCUITPY drive
- Install libraries with circup
- Connect 64x32 RGB LED matrix

### 2. Setup Camera Source (macOS)

```bash
cd sandbox
uv venv
source .venv/bin/activate
uv pip install opencv-python numpy pyserial
python camera_feed.py
```

### 3. Setup Camera Source (Raspberry Pi)

```bash
cd pi
uv venv
source .venv/bin/activate
uv pip install opencv-python numpy pyserial picamera2
python camera_feed.py
```

## Keyboard Controls

Single keypress controls (no Enter needed):

> **Note:** Single-keypress input currently works on Mac/Linux only. Windows support planned for future.

**Display Modes:**
| Key | Mode |
|-----|------|
| `c` | **Crop/Landscape** (default) - center crop to 2:1 ratio |
| `s` | **Squish** - stretches to fit, may distort |
| `l` | **Letterbox** - maintains aspect ratio, black bars |
| `p` | **Portrait** - for rotated display |

**Effects:**
| Key | Action |
|-----|--------|
| `b` | **Black & white** mode |
| `n` | **Normal** (color) mode |

**Actions:**
| Key | Action |
|-----|--------|
| `Space` | Take a snapshot (3-2-1 countdown, saves to disk) |
| `Space`/`r` | During snapshot: **cancel** countdown or resume early |
| `v` | **Avatar capture mode** - guided multi-pose capture session |
| `d` | Toggle **debug** mode (frame rate display on/off) |
| `r` | **Reset** to defaults (landscape, color, debug on) |
| `h` | Show **help** and current settings |
| `q` | **Quit** the application |
| `Ctrl+C` | Force stop |

## Display Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **Landscape** (default) | Center crops to 2:1 ratio | Normal horizontal display |
| **Portrait** | Center crops to 1:2 ratio, rotates 90° | Rotated vertical display |
| **Squish** | Stretches entire frame to fit | Seeing everything (accepts distortion) |
| **Letterbox** | Maintains aspect ratio, black bars fill space | No distortion, no cropping |

## Snapshot Feature

Press `Space` to capture a snapshot:
1. **3-2-1 countdown** appears on the display (red numbers)
2. **Clean frame captured** (no overlay)
3. **Files saved** to current directory:
   - `snapshot_YYYYMMDD_HHMMSS.bmp` - Color image
   - `snapshot_YYYYMMDD_HHMMSS_rgb565.bin` - Raw RGB565 data
4. **5-second pause** before resuming

## Avatar Capture Mode

Press `v` to enter guided avatar capture mode for creating a digital avatar:

1. **Voice prompts** guide you through 18 poses (angles + expressions)
2. **Controls during capture:**
   - `Space` = Capture current pose
   - `S` = Skip this pose
   - `R` = Repeat voice prompt
   - `Q` = Quit avatar mode
3. **Files saved** to `avatar_YYYYMMDD_HHMMSS/` folder:
   - Individual pose images (`avatar_front_neutral.bmp`, etc.)
   - RGB565 versions for direct LED playback
   - `manifest.json` with session metadata

**Tip:** Press `p` for portrait mode before starting - faces fit better in 32x64!

**Voice engines used:**
- macOS: `say` command with Zarvox voice (robot)
- Linux: `espeak-ng` with robotic settings
- Windows: `pyttsx3` (install with `pip install pyttsx3`)

See `proposals/digital-avatar.md` for the full avatar generation proposal.

## Project Structure

```
ledportal/
├── sandbox/               # Sandbox/playground application
│   ├── camera_feed.py     # Main camera capture and sender
│   └── config.py          # Configuration settings
│
├── pi/                    # Raspberry Pi application
│   ├── camera_feed.py     # Main camera capture and sender
│   └── config.py          # Configuration settings
│
├── hs/                    # High School learning version
│   ├── README.md          # Setup and learning guide
│   ├── REQUIREMENTS.md    # Prompts used to generate, why learn Python
│   ├── mac/               # Educational macOS version
│   └── pi/                # Educational Pi version
│
├── pro/                   # Professional version
│   ├── README.md          # Setup with uv, ruff, ty
│   ├── pyproject.toml     # Astral tooling configuration
│   ├── Makefile           # Development commands
│   └── src/ledportal_pro/ # Modular package structure
│
├── matrix-portal/         # Matrix Portal M4 (CircuitPython)
│   ├── boot.py            # Enable USB data port
│   └── code.py            # Frame receiver and display
│
├── CLAUDE.md              # AI assistant instructions
├── code_use.md            # Version comparison (HS vs Pro)
└── README.md              # This file
```

## Performance

- **Target FPS**: 5 FPS
- **Baud Rate**: 2,000,000 bps
- **Frame Size**: 4,096 bytes (64 × 32 × 2)
- **Latency**: ~200ms typical

## Configuration

Edit `config.py` in sandbox/ or pi/:

```python
MATRIX_WIDTH = 64       # LED matrix width
MATRIX_HEIGHT = 32      # LED matrix height
CAMERA_WIDTH = 640      # Camera capture width
CAMERA_HEIGHT = 480     # Camera capture height
TARGET_FPS = 5          # Target frames per second
```

## Troubleshooting

### Camera not found
- Close other apps using the camera (Zoom, FaceTime)
- Try a different camera index: edit `setup_camera(camera_index=1)`

### Matrix Portal not found
- Check USB connection
- Verify the Matrix Portal shows "WAITING FOR USB" on display
- Run `python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"`

### Low frame rate
- Ensure baud rate is 2,000,000 in both sender and receiver
- Disable frame limiting: set `ENABLE_FRAME_LIMITING = 0`
- Check CPU usage on the host computer

### Colors look wrong
- Verify RGB565 format is used (not RGB565_SWAPPED)
- Check the color converter in matrix-portal/code.py

## Documentation

- `CLAUDE.md` - Project guidelines for AI assistants
- `code_use.md` - Comparison of educational vs professional code
- `hs/REQUIREMENTS.md` - Why learn Python even with AI?
- `hs/README.md` - High school version setup and exercises
- `pro/README.md` - Professional version setup with Astral tools
