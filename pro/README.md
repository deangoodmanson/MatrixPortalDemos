# LED Portal Pro

Professional LED Matrix camera feed system for Raspberry Pi and macOS.

Captures video from a camera, processes it, and displays on a 64x32 RGB LED matrix via an Adafruit Matrix Portal M4 controller.

## Features

- Cross-platform support (macOS, Raspberry Pi)
- Pi Camera and USB camera support
- RGB565 color conversion for LED matrix
- Three display modes: landscape, portrait, letterbox
- Snapshot capture with 3-2-1 countdown
- Avatar capture mode with guided voice prompts
- Black and white mode
- Cross-platform text-to-speech (macOS say, Linux espeak-ng, Windows pyttsx3)
- YAML configuration
- Type-safe Python code
- 136-test unit test suite

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

### Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

### Install LED Portal Pro

```bash
cd pro

# Install dependencies
uv sync

# Or install with development tools
uv sync --all-extras
```

### Raspberry Pi Additional Setup

For Pi Camera support on Raspberry Pi:

```bash
# Install with Pi Camera support
uv sync --extra pi
```

## Raspberry Pi Workflows

### Option 1: VS Code Remote SSH (Recommended)

Develop on your Mac/PC while testing on real Pi hardware:

```bash
# 1. On your Mac - Install "Remote - SSH" extension in VS Code

# 2. Add Pi to SSH config (~/.ssh/config):
Host pi-ledportal
    HostName 192.168.1.xxx  # Your Pi's IP
    User pi
    ForwardAgent yes

# 3. In VS Code:
#    - CMD+Shift+P → "Remote-SSH: Connect to Host" → pi-ledportal
#    - Open folder: /home/pi/projects/ledportal
#    - Edit and run directly on Pi with full VS Code features!
```

**Advantages:**
- ✅ Full VS Code IntelliSense, debugging, git
- ✅ Code runs on actual Pi hardware (camera, serial port)
- ✅ No file syncing needed

### Option 2: Git Clone on Pi

Standard development workflow:

```bash
# On Raspberry Pi
git clone https://github.com/deangoodmanson/MatrixPortalDemos.git
cd MatrixPortalDemos/pro

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Pi Camera requires system packages
sudo apt install -y python3-picamera2

# Run
uv run ledportal
```

### Option 3: Hybrid Development

Develop on Mac, test on Pi:

```bash
# On Mac - make changes, commit
git add .
git commit -m "Test camera feature"
git push

# On Pi - pull and test
git pull
uv run ledportal
```

### Pi Camera Testing

```bash
# Camera features ONLY work on actual Pi hardware
# Quick test:
python3 -c "from picamera2 import Picamera2; cam = Picamera2(); print('Camera OK')"

# Run with Pi camera
uv run ledportal --config config/pi.yaml
```

## Usage

### Run with default configuration

```bash
uv run ledportal
```

### Run with platform-specific config

```bash
# macOS
uv run ledportal --config config/mac.yaml

# Raspberry Pi
uv run ledportal --config config/pi.yaml
```

### Command Line Options

```
usage: ledportal [-h] [--config CONFIG] [--frames FRAMES] [--no-display]
                 [--camera CAMERA] [--port PORT] [--bw]
                 [--orientation {landscape,portrait}]
                 [--processing {center,stretch,fit}]

LED Portal Pro - Camera feed for LED matrix display

options:
  -h, --help            show this help message and exit
  --config, -c CONFIG   Path to YAML configuration file
  --frames, -n FRAMES   Number of frames to capture (0 for infinite)
  --no-display          Start with display output paused (toggle with 't' key)
  --camera CAMERA       Camera index to use (overrides config)
  --port PORT           Serial port to use (overrides auto-detection)
  --bw                  Start in black and white mode
  --orientation {landscape,portrait}
                        Display orientation (overrides config)
  --processing {center,stretch,fit}
                        Processing mode (overrides config)
```

### Interactive Controls

Single keypress (no Enter needed, Mac/Linux only):

**Orientation:**

| Key | Mode |
|-----|------|
| `l` | Landscape (wide, default) |
| `p` | Portrait (tall, rotated 90°) |

**Processing:**

| Key | Mode |
|-----|------|
| `c` | Center crop (default) |
| `s` | Stretch to fit |
| `f` | Fit with letterbox |

**Effects:**

| Key | Action |
|-----|--------|
| `b` | Toggle black & white / color |
| `z` | Cycle zoom (100% → 75% → 50% → 25%) |

**Actions:**

| Key | Action |
|-----|--------|
| `Space` | Snapshot (3-2-1 countdown, saves BMP) |
| `v` | Avatar capture mode (guided 18-pose session with voice prompts) |
| `t` | Toggle display output |
| `d` | Toggle debug stats |
| `r` | Reset to defaults |
| `h` | Show help |
| `q` | Quit |

## Configuration

Configuration is via YAML files. See `config/default.yaml` for all options.

Key settings:

```yaml
matrix:
  width: 64
  height: 32

camera:
  width: 0     # 0 = use native resolution (recommended)
  height: 0    # 0 = use native resolution (recommended)
  index: 0
  prefer_picamera: true  # Use Pi Camera on Raspberry Pi

target_fps: 30
```

## Development

### Code Quality Tools

This project uses Astral's tools:

- **uv**: Package management
- **ruff**: Linting and formatting
- **ty**: Type checking

### Run Checks

```bash
# Run linter
make lint

# Format code
make format

# Run type checker
make typecheck

# Run all checks (lint + format + typecheck)
make check
```

### Unit Tests

136 tests covering all non-hardware modules. No camera or serial port required.

```bash
# Run tests
make test

# Or directly
uv run pytest tests/ -v
```

**What's tested:**

| Module | Tests | Focus |
|--------|-------|-------|
| `config` | 13 | Defaults, YAML round-trip, error handling |
| `processing/color` | 17 | RGB565 bit-exact encoding, grayscale, gamma |
| `processing/resize` | 25 | All 3 modes × varied input shapes, letterbox black bars |
| `processing/patterns` | 11 | Byte counts, color distinctness, uniformity |
| `ui/input` | 24 | Every key binding, line-mode fallback, enum completeness |
| `ui/overlay` | 9 | Non-mutation, shape, pixel-level drawing |
| `ui/snapshot` | 5 | File creation, naming, content |
| `ui/avatar` | 8 | Pose definitions, manifest JSON |
| `ui/tts` | 7 | Platform dispatch (mocked), silent failure |
| `exceptions` | 5 | Hierarchy, catchability |

**Intentionally not unit tested:** `capture/` and `transport/` — these require real hardware (camera, serial port) and belong in integration tests.

### Using Make

```bash
# See all available commands
make help

# Install development dependencies
make install-dev

# Run with macOS config
make run-mac

# Run with display paused (camera only)
make run-test
```

## Project Structure

```
pro/
├── pyproject.toml          # Project configuration (uv, ruff, ty, pytest)
├── Makefile                # Development commands
├── README.md               # This file
├── config/                 # YAML configuration files
│   ├── default.yaml
│   ├── mac.yaml
│   └── pi.yaml
├── tests/                  # Unit tests (136 tests, no hardware required)
│   ├── conftest.py         # Shared fixtures
│   ├── test_config.py
│   ├── test_color.py
│   ├── test_resize.py
│   ├── test_patterns.py
│   ├── test_input.py
│   ├── test_overlay.py
│   ├── test_snapshot.py
│   ├── test_avatar.py
│   ├── test_exceptions.py
│   └── test_tts.py
└── src/
    └── ledportal_pro/
        ├── __init__.py
        ├── main.py         # Entry point and main loop
        ├── config.py       # Configuration management (dataclasses + YAML)
        ├── exceptions.py   # Custom exception hierarchy
        ├── capture/        # Camera interfaces
        │   ├── base.py     # Abstract camera base class
        │   ├── opencv.py   # OpenCV VideoCapture camera
        │   ├── picamera.py # Raspberry Pi picamera2
        │   └── factory.py  # Camera creation (auto-detects platform)
        ├── transport/      # Serial communication
        │   ├── base.py     # Abstract transport base class
        │   ├── serial.py   # USB CDC serial transport
        │   └── factory.py  # Transport creation
        ├── processing/     # Image processing pipeline
        │   ├── resize.py   # Frame resizing (4 display modes)
        │   ├── color.py    # RGB565 conversion, grayscale, gamma
        │   └── patterns.py # Test pattern generators
        └── ui/             # User interface layer
            ├── input.py    # Single-keypress keyboard handling
            ├── overlay.py  # Frame text overlays
            ├── snapshot.py # Snapshot file management
            ├── avatar.py   # Guided avatar capture session
            └── tts.py      # Cross-platform text-to-speech
```

## License

MIT License
