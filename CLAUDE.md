# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Real-time camera feed display system for a **64×32 RGB LED matrix** via Adafruit Matrix Portal M4/S3 controller.

**Target Performance**: 10-24 FPS at 64×32 resolution with <200ms latency

## Project Structure

This repository contains **three distinct versions**:

### 1. `pro/` - Professional Version
- **Purpose**: Production-ready, modular application
- **Python**: 3.14+ with strict type checking (ty)
- **Tooling**: uv, ruff, pytest (136 tests)
- **Architecture**: Modular with separate packages (capture, transport, processing, ui)
- **Config**: YAML-based configuration
- **Target**: Developers, production deployment

### 2. `hs/` - High School Educational Version
- **Purpose**: Educational, learning-focused
- **Python**: 3.14+ (modern but accessible)
- **Tooling**: uv (teaching modern practices)
- **Architecture**: Single-file with extensive comments
- **Config**: Simple constants in config.py
- **Target**: Students, beginners, learning Python

### 3. `matrix-portal/` - Firmware
- **CircuitPython 10** code for Matrix Portal M4/S3
- Receives frames via USB CDC serial
- Displays on 64×32 RGB LED matrix

### 4. `utils/` - Shared Utilities
- **Purpose**: Snapshot processing utilities
- **Library**: ledportal-utils (local package)
- **Functions**: export_png(), export_blocks(), export_circles()
- **Testing**: 23 unit tests with pytest

## Development Philosophy

**This is an educational demonstration project.**

- **Prioritize clarity** over clever optimization
- **Two audiences**: Students (hs) and Developers (pro)
- **Modern practices**: Use current Python, uv, type hints
- **Keep it simple**: No over-engineering
- **Educational value**: Code should teach good practices

## System Architecture

### Communication Protocol
- **Transport**: USB CDC Serial (4M baud)
- **Not using**: PyUSB bulk transfers (old approach)
- **Format**: Raw RGB565 bytes (4,096 bytes per frame)
- **Platform**: Works on macOS, Linux, Windows, Raspberry Pi

### Data Flow
```
Camera → Python (Capture) → Process/Resize (64×32) → RGB565 → USB Serial → Matrix Portal → LED Matrix
```

### Frame Format
- **Resolution**: 64×32 pixels (2,048 pixels, not 32×64!)
- **Color Format**: RGB565 (16-bit, 4,096 bytes/frame)
- **Orientation**: Landscape (64 wide) or Portrait (rotated 90° CW)

## Tooling Stack

### Pro Version
- **uv**: Package and Python version management
- **ruff**: Linting and formatting (Astral)
- **ty**: Type checking and language server / LSP (Astral)
- **pytest**: Testing framework (136 tests)
- **Make**: Development task automation

### HS Version
- **uv**: Python installation and package management
- **Simple**: No build complexity, teaches fundamentals
- **Focus**: Learning Python, understanding image processing

### Utils Library
- **uv**: Package management
- **ruff**: Code quality and formatting (Astral)
- **ty**: Type safety and language server / LSP (Astral)
- **pytest**: 23 unit tests
- **Pillow**: Image processing

## Key Technical Patterns

### Display Modes
- **Orientation**: Landscape (wide) or Portrait (tall, rotated 90° CW)
- **Processing**: Center crop, Stretch, or Fit (letterbox)
- **Effects**: Color or Black & White

### Snapshot System
- **User snapshots**: Properly oriented for PC viewing (rotated back if portrait)
- **Debug files**: Raw 64×32 frame + RGB565 binary (only in debug mode)
- **Utilities**: Can export as blocks or circles (ledportal-utils)

### Camera Support
- **Raspberry Pi**: picamera2 (preferred) or USB camera (OpenCV)
- **Mac/PC**: USB camera via OpenCV
- **Auto-detection**: Code tries picamera2 first, falls back to OpenCV

## Development Workflows

### Working on Pro Version
```bash
cd pro
uv sync
uv run ledportal --config config/mac.yaml
```

### Working on HS Version
```bash
cd hs/src
uv venv
source .venv/bin/activate
uv pip install opencv-python pyserial numpy pillow
python camera_feed.py
```

### Testing on Raspberry Pi
**Recommended**: VS Code Remote SSH
- Develop on Mac with full IDE features
- Code runs on actual Pi hardware (camera, serial port)
- No file syncing needed

**Alternative**: Git clone + uv on Pi

### Creating Pull Requests
- Use `gh pr create` with detailed descriptions
- Include test plan
- Reference related issues
- Add "Co-Authored-By: Claude Sonnet 4.5"

## Code Guidelines

### Pro Version
- **Type hints**: All functions must have type annotations
- **Docstrings**: Google-style docstrings
- **Testing**: Write tests for non-hardware modules
- **Modules**: Separate concerns (capture, transport, processing, ui)

### HS Version
- **Comments**: Extensive explanatory comments for students
- **Simplicity**: Avoid abstractions, keep code linear
- **Educational**: Include "what's happening" explanations
- **Type hints**: Use but keep simple (Optional, Tuple, etc.)

### Utils Library
- **Type safe**: Strict type checking with ty
- **Tested**: Comprehensive pytest coverage
- **Documented**: Clear docstrings with examples
- **Pillow**: Use PIL for image processing (not OpenCV for utils)

## Testing Philosophy

### Pro Version (136 tests)
- **Unit tests**: All non-hardware modules
- **No mocking**: Hardware modules (capture, transport) not unit tested
- **Fast**: Tests run in <1 second
- **Comprehensive**: Every function, edge cases, error handling

### Utils Library (23 tests)
- **Fixtures**: Temporary directories, sample BMP files
- **Validation**: Pixel-level correctness, dimensions, file creation
- **Coverage**: All three export functions + edge cases

## Common Tasks

### Add new processing mode
1. Update `processing/resize.py` with new mode
2. Add to `ProcessingConfig` enum
3. Write tests in `test_resize.py`
4. Update keyboard handler in `ui/input.py`
5. Update help text

### Add new snapshot utility
1. Add function to `utils/src/ledportal_utils/snapshot.py`
2. Export in `__init__.py`
3. Write tests in `utils/tests/test_snapshot.py`
4. Update `utils/README.md` with example
5. Test with real snapshot files

### Update for new Python version
- Pro: Update `requires-python` in `pro/pyproject.toml`
- HS: Just works with uv's auto-install
- Utils: Update `utils/pyproject.toml` if needed

## Important Notes

- **Resolution is 64×32**: Width=64, Height=32 (landscape default)
- **Serial not bulk**: USB CDC serial communication, not PyUSB bulk
- **Two versions**: Keep pro and hs in sync for features, but different styles
- **Modern Python**: Use Python 3.14+ minimum, teach current practices
- **uv everywhere**: Both pro and hs now use uv for Python management
- **Pillow for utils**: Use PIL for snapshot processing utilities

## Hardware Details

- **Raspberry Pi 3/4/5**: Runs Python code, connects via USB
- **Matrix Portal M4 or S3**: CircuitPython, receives via USB serial
- **64×32 RGB LED Matrix**: HUB75 interface, connected to Matrix Portal
- **Camera**: Pi Camera module (preferred) or USB webcam
