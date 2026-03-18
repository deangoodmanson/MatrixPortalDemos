# LED Portal Pro

Professional LED Matrix camera feed system for Raspberry Pi and macOS.

Captures video from a camera, processes it, and displays on a 64x32 RGB LED matrix via an Adafruit Matrix Portal M4 controller.

## Features

- Cross-platform support (macOS, Raspberry Pi, Linux, Windows)
- Pi Camera and USB camera support with auto-detection
- RGB565 color conversion for LED matrix
- Orientation: landscape and portrait (90° CW rotation)
- Processing modes: center crop, stretch, fit (letterbox)
- Effects: black & white, mirror, zoom (100/75/50/25%), render algorithm cycling, LED size control
- Snapshot capture with 3-2-1 countdown (BMP + PDF export)
- Avatar capture mode with guided voice prompts
- Demo mode: auto, manual (step-by-step), and pausable
- Side-by-side preview window with multiple LED render modes
- Cross-platform text-to-speech (macOS say, Linux espeak-ng, Windows pyttsx3)
- YAML configuration with CLI overrides
- Type-safe Python code (checked with `ty`)
- 187-test unit test suite

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

No LED matrix hardware is required. The app runs with just a webcam — use the
preview window (`w`) to see the LED simulation on screen. Use `--no-display` to
skip serial port detection entirely.

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
                 [--processing {center,stretch,fit}] [--no-debug] [--no-save]

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
  --no-debug            Disable debug/stats output (toggle with 'd' key)
  --no-save             Disable saving snapshots to disk (countdown still runs)
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
| `m` | Toggle mirror (horizontal flip) |
| `z` | Cycle zoom (100% → 75% → 50% → 25%) |

**Preview:**

| Key | Action |
|-----|--------|
| `w` | Toggle preview window on/off |
| `o` | Cycle preview render mode (see table below) |
| `+` / `=` | Increase LED size (Circles mode only) |
| `-` / `_` | Decrease LED size (Circles mode only) |

**Actions:**

| Key | Action |
|-----|--------|
| `Space` | Snapshot (3-2-1 countdown, saves BMP + PDF) |
| `v` | Avatar capture mode (guided 18-pose session with voice prompts) |

**Demo:**

| Key | Action |
|-----|--------|
| `x` | Toggle auto demo mode (cycles through all features) |
| `Shift+X` | Start manual demo mode |
| `.` / `>` | Next demo step |
| `,` / `<` | Previous demo step |
| `Space` | Pause/resume auto demo |

**System:**

| Key | Action |
|-----|--------|
| `t` | Toggle transmission (pause/resume sending to LED matrix, or reconnect) |
| `d` | Toggle debug stats |
| `w` | Toggle preview window |
| `r` | Reset to defaults |
| `h` | Show help |
| `q` | Quit |

**Preview render modes** (`o` key cycles through):

Each mode controls how the 64×32 LED frame is drawn in the right-hand pane of
the preview window. Circle sizes are expressed as a percentage of the LED cell
diameter (cell = 10×10 px at 10× scale).

| Mode | Diameter | Radius | Gaps | Rendering |
|------|----------|--------|------|-----------|
| Squares | — | — | none (filled) | nearest-neighbour resize |
| Circles 50% | 5 px | 2.5 px | wide | vectorised mask |
| Circles 75% | 7.5 px | 3.75 px | clear | vectorised mask |
| Circles 100% | 10 px | 5 px | none (tangent) | vectorised mask |
| Circles 125% | 12.5 px | 6.25 px | overlap ~2.5 px | painter's algorithm |
| Circles ~141% (corner) | ≈14.1 px | ≈7.07 px (int: 8) | overlap at corners | painter's algorithm |
| Gaussian blur | σ ≈ 2.7 px | — | soft glow | point-source + GaussianBlur |

> Modes ≤ 100% are rendered with a fast vectorised NumPy mask.
> Modes > 100% use painter's algorithm (2 048 `cv2.circle` calls) so that
> overlapping regions between adjacent LEDs are drawn correctly.
> Gaussian blur uses a point-source model with σ ≈ 27% of cell width,
> calibrated to match the measured diffuser panel (FWHM ≈ 63% of cell,
> gap/peak ratio ≈ 37%).

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

processing:
  max_brightness: 255   # 0-255; full brightness. Reduce to 128 if USB-powered Pi
                        # browns out (all LEDs white at 64×32 can draw ~3A)

target_fps: 30
```

## Development

### Code Quality Tools

This project uses [Astral's](https://astral.sh) full toolchain:

- **uv**: Package and Python version management (`uv sync`, `uv run`)
- **ruff**: Linting and formatting (`ruff check`, `ruff format`)
- **ty**: Type checking — extremely fast, written in Rust ([docs](https://docs.astral.sh/ty/))

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

### Type Checking Notes

`ty` is configured in `pyproject.toml` under `[tool.ty]`:

```toml
[tool.ty.rules]
unresolved-import = "ignore"   # picamera2 is Pi-only, not installed on Mac
invalid-return-type = "warn"   # OpenCV stubs are imprecise (cv2 returns generic arrays)
unsupported-operator = "ignore"
```

Expected clean run:
```
$ make typecheck
All checks passed!
```

### Unit Tests

187 tests covering all non-hardware modules. No camera or serial port required.

```bash
# Run tests
make test

# Or directly
uv run pytest tests/ -v
```

**What's tested:**

| Module | Tests | Focus |
|--------|-------|-------|
| `ui/input` | 48 | Every key binding, demo keys, line-mode fallback, enum completeness |
| `processing/resize` | 37 | All 3 modes × varied input shapes, letterbox black bars |
| `processing/color` | 22 | RGB565 bit-exact encoding, grayscale, gamma |
| `ui/overlay` | 22 | Non-mutation, shape, pixel-level drawing |
| `config` | 15 | Defaults, YAML round-trip, error handling |
| `processing/patterns` | 11 | Byte counts, color distinctness, uniformity |
| `ui/avatar` | 8 | Pose definitions, manifest JSON |
| `processing/zoom` | 7 | Zoom level cycling, crop calculations |
| `ui/tts` | 7 | Platform dispatch (mocked), silent failure |
| `ui/snapshot` | 5 | File creation, naming, content |
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
├── tests/                  # Unit tests (187 tests, no hardware required)
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
│   ├── test_tts.py
│   └── test_zoom.py
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
        │   ├── resize.py   # Frame resizing (center, stretch, fit)
        │   ├── color.py    # RGB565 conversion, grayscale, gamma
        │   ├── zoom.py     # Zoom level cycling and crop calculations
        │   └── patterns.py # Test pattern generators
        └── ui/             # User interface layer
            ├── input.py    # Single-keypress keyboard handling
            ├── overlay.py  # Frame text overlays
            ├── snapshot.py # Snapshot file management (BMP + PDF)
            ├── avatar.py   # Guided avatar capture session
            ├── demo.py     # Demo mode (auto, manual, pausable)
            └── tts.py      # Cross-platform text-to-speech
```

## License

MIT License
