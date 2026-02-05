# Mac Camera Feed (Python 3.14 with uv)

Captures webcam frames and sends them to the LED Matrix display via Matrix Portal.

## Prerequisites

1. **Python 3.14** via uv
2. **Webcam** (built-in or USB)
3. **Camera permissions** - Grant camera access to Terminal in System Settings
4. **Adafruit Matrix Portal M4** connected via USB (optional for testing)

### Important: Camera Permissions on macOS

Before running, you **must** grant camera access:
1. Open **System Settings** → **Privacy & Security** → **Camera**
2. Enable camera for your terminal app (Terminal, iTerm2, etc.)
3. Restart your terminal after granting permissions

## Setup

### Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install dependencies

The easiest way is to use `uv run` which automatically handles the virtual environment:

```bash
cd mac
uv run camera_feed.py
```

This will automatically:
- Create a virtual environment (`.venv/`)
- Install dependencies from `pyproject.toml`
- Run the script

Alternatively, manually create the environment:

```bash
cd mac
uv venv --python 3.14
source .venv/bin/activate
uv pip install numpy opencv-python pyserial
```

## Usage

### Run the camera feed

```bash
# With virtual environment activated
python camera_feed.py

# Or using uv run directly
uv run camera_feed.py
```

The script will:
- Open your default webcam (camera 0)
- Capture frames at target 10 FPS
- Resize to 32x64 pixels
- Convert to RGB565 format
- Send to Matrix Portal M4 via USB (if connected)

Press Ctrl+C to stop.

### Check camera permissions and availability

```bash
uv run check_camera.py
```

This will verify camera is accessible and permissions are granted.

### Test camera without Matrix Portal M4

```bash
uv run test_camera.py
```

This saves a test frame as `test_frame.png` to verify camera capture works.

### List USB devices

```bash
python list_usb_devices.py
# or
uv run list_usb_devices.py
```

Shows all USB serial devices. The Matrix Portal M4 should appear as:
- `/dev/cu.usbmodem...` (CircuitPython CDC data)

## Configuration

Edit `config.py` to adjust:
- `MATRIX_WIDTH`, `MATRIX_HEIGHT` - Display dimensions
- `CAMERA_WIDTH`, `CAMERA_HEIGHT` - Capture resolution
- `TARGET_FPS` - Target frame rate (default: 10)

## Selecting a different camera

By default, camera 0 is used. To use a different camera:

```python
# Edit camera_feed.py
camera = setup_camera(camera_index=1)  # Use camera 1
```

## Troubleshooting

### "Not authorized to capture video" error
**This is the most common issue on macOS.**

1. Open **System Settings** → **Privacy & Security** → **Camera**
2. Find your terminal app (Terminal, iTerm2, VS Code, etc.)
3. Enable the toggle for camera access
4. **Restart your terminal completely** (quit and reopen)
5. Run `uv run check_camera.py` to verify

### No webcam found
- Run `uv run check_camera.py` to diagnose the issue
- Check camera works in Photo Booth app first
- Try a different camera index if you have multiple cameras

### Matrix Portal M4 not found
- Run `python list_usb_devices.py` to see available devices
- Make sure CircuitPython is installed on Matrix Portal M4
- Check USB cable supports data (not just power)
- Look for `/dev/cu.usbmodem*` devices

### Low frame rate
- Camera processing may be slow on older Macs
- Try reducing `TARGET_FPS` in `config.py`
- Check Activity Monitor for CPU usage

### uv commands not working
- Make sure uv is installed: `uv --version`
- Update uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Verify Python 3.14 is available: `uv python list`

## Development with uv

### Add new dependencies

```bash
uv add package-name
```

### Update dependencies

```bash
uv pip compile pyproject.toml -o requirements.txt
uv pip sync requirements.txt
```

### Run with specific Python version

```bash
uv run --python 3.14 camera_feed.py
```

## macOS-Specific Notes

- Webcam access requires camera permissions
- USB serial ports appear as `/dev/cu.usbmodem*` devices
- Built-in FaceTime camera is usually camera 0
- External USB cameras typically start at camera 1
