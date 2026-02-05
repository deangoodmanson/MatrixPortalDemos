# Raspberry Pi Camera Feed

Captures camera frames and converts them for the LED Matrix display.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python camera_feed.py
```

The script will:
- Auto-detect Pi Camera or USB camera
- Capture frames at target 10 FPS
- Resize to 32x64 pixels
- Convert to RGB565 format
- Send to Matrix Portal M4 via USB

Press Ctrl+C to stop.

## USB Connection

The script auto-detects the Matrix Portal M4 by looking for a "CircuitPython" USB serial device.

To see available USB devices:

```bash
python list_usb_devices.py
```

The Matrix Portal M4 should appear as "CircuitPython CDC data" port.

## Testing

To test camera capture and conversion without the Matrix Portal:

```bash
python test_camera.py
```

This will save a test frame as `test_frame.png` to verify the resize and color conversion.

## Troubleshooting

**Matrix Portal M4 not found:**
- Make sure CircuitPython is installed on the Matrix Portal M4
- Check that the USB cable supports data (not just power)
- Run `python list_usb_devices.py` to see available devices
- On Linux, you may need udev rules for permissions

**Low frame rate:**
- Check USB connection quality
- Try reducing TARGET_FPS in config.py
- Camera processing may be the bottleneck on older Pi models
