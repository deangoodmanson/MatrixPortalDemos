# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-02-23

### Connection UX

- `t` key now reconnects in one press when display is enabled but portal is disconnected (previously required two presses)
- Loud `!!!` banners on portal disconnect and failed reconnect, each with a `press 't'` prompt
- Startup message when portal not found includes `press 't' to connect when ready`
- Paused message now reads `press 't' to resume`
- All failed reconnect attempts followed by `press 't' to try again` prompt

### Terminology

- Renamed `toggle display` → `toggle transmission` across all help text and READMEs (more accurate: matrix holds last frame; only frame sending stops)

### Preview Window

- Blue 1-pixel border on camera side of preview shows the exact region being sent to the matrix portal
- Center mode: inner crop rectangle reflecting the actual aspect-ratio crop
- Stretch/fit modes: full-image border (entire frame is used)
- Both Pro and HS versions updated

### Python & Tooling

- Minimum Python version bumped to 3.14 for both Pro and HS
- Updated ruff 0.14.14 → 0.15.2, ty 0.0.14 → 0.0.18, opencv 4.13.0.90 → 4.13.0.92, pillow 12.1.0 → 12.1.1

### Bug Fixes

- Silent camera frame drops (transient, self-recovering — no warning printed)
- Fixed two-press reconnect bug in `t` key handler

## [0.1.0] - 2026-02-22

Initial release of the LED Matrix Portal Camera Feed system.

### System

- Real-time camera feed displayed on a 64×32 RGB LED matrix via Adafruit Matrix Portal M4
- USB CDC serial communication at 4,000,000 baud
- ~24 FPS achieved (optimized from initial 5 FPS baseline using `bitmaptools.arrayblit`)
- Cross-platform: macOS, Raspberry Pi, Linux, Windows

### Pro Version (`pro/`)

- Modular Python package (`ledportal-pro`) with `uv`, `ruff`, `ty`, and `pytest`
- Capture: OpenCV (USB camera) and picamera2 (Pi Camera) with auto-detection
- Transport: USB CDC serial with DTR reset handling and buffer flush
- Processing: center crop, stretch, and letterbox (fit) display modes
- Orientation: landscape and portrait (90° CW rotation)
- Effects: black & white, zoom (100/75/50/25%)
- Snapshot: 3-2-1 countdown, saves oriented BMP, 5-second preview
- Avatar capture: guided 18-pose session with voice prompts
- Display toggle (`t` key): pause/resume sending to matrix, reconnect on re-enable
- YAML configuration with separate `mac.yaml` and `pi.yaml` profiles
- Native camera resolution by default (`width: 0` / `height: 0`)
- Camera detection at startup: lists all available cameras with resolution and FPS
- Brightness limiting for USB-powered configurations
- 159 unit tests covering all non-hardware modules
- Type-safe with `ty` (Astral); clean pass with zero errors

### HS Version (`hs/`)

- Single-file educational Python application (`camera_feed.py`)
- Extensive inline comments explaining every concept for students
- Same feature set as Pro: all display modes, snapshot, avatar, display toggle
- Key bindings: `l/p` orientation, `c/s/f` processing, `b` B&W, `z` zoom, `t` toggle transmission, `r` reset, `space` snapshot, `v` avatar, `d` debug, `h` help, `q` quit
- Developer tooling (`hs/pyproject.toml`) with `ty` and `ruff` — students unaffected
- Type-safe: `Optional[serial.Serial]` throughout serial-accepting functions

### Firmware (`matrix-portal/`)

- CircuitPython code for Adafruit Matrix Portal M4
- Receives RGB565 frames over USB CDC serial (`usb_cdc.data`)
- `bitmaptools.arrayblit` for high-performance memory copy (~24 FPS)
- Self-check: UP button displays kitten test image for 5 seconds
- Boot message: "WAITING FOR USB" on startup

### Utilities (`utils/`)

- `ledportal-utils` library (`v0.1.0`) for post-processing snapshots
- `export_png()`: convert BMP snapshots to PNG
- `export_blocks()`: pixelated block display effect
- `export_circles()`: circular LED simulation effect
- 23 unit tests

### Infrastructure

- MIT License
- GitHub Actions CI: automated tests, lint, type check for `pro/`, `hs/`, and `utils/` on every push and PR
- `.gitignore` covering Python, IDE, OS, secrets, and project artifacts
