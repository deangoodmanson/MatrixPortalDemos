# Matrix Portal M4 Frame Display

CircuitPython application for Adafruit Matrix Portal M4 to receive and display camera frames.

## Setup

1. Install CircuitPython on your Adafruit Matrix Portal M4
2. Install `circup` on your computer: `pip install circup`
3. Copy both `boot.py` and `code.py` to the CIRCUITPY drive
4. Install required libraries: `circup install adafruit_display_text`
5. Reset the Matrix Portal M4 for boot.py to take effect

**Important:** The `boot.py` file enables the USB data port needed to receive frames.

## Required CircuitPython Libraries

### Option 1: Install with circup (Recommended)

Install circup on your computer:
```bash
pip install circup
# or
pip3 install --user circup
```

Then install the required libraries to your Matrix Portal M4:
```bash
circup install adafruit_display_text adafruit_imageload
```

Verify installation:
```bash
circup freeze
```

### Option 2: Manual Installation

Download the library bundle from https://circuitpython.org/libraries and copy to the `lib/` folder on CIRCUITPY:

- `adafruit_display_text/` (for text display)
- `adafruit_imageload/` (for loading BMP images)
- `adafruit_bitmap_font/` (dependency for display_text)
- `adafruit_ticks.mpy` (dependency for display_text)

### Built-in Libraries

The following are built-in to CircuitPython (no installation needed):
- `rgbmatrix`
- `framebufferio`
- `displayio`
- `usb_cdc`
- `terminalio`

## Hardware Setup

Connect the 32x64 RGB LED matrix to the Matrix Portal M4 using the HUB75 connector.

## How It Works

1. On startup, displays "WAITING FOR USB" message in green
2. Matrix Portal M4 exposes a USB CDC (serial) data port
3. Receives RGB565 frame data (4,096 bytes per frame)
4. Switches to frame display when first frame arrives
5. Updates the LED matrix at maximum 5 FPS
6. Press the **UP button** to display the kitten test image for 5 seconds (self-check)

## Converting Images for the Matrix

To display custom images on the 64x32 LED matrix, convert them to BMP format using the `sips` command (built-in on macOS):

```bash
# Resize and convert any image to 64x32 BMP
sips -z 32 64 input_image.png --out output_name.bmp -s format bmp
```

Example:
```bash
# Convert kitten.png to 64x32 BMP
sips -z 32 64 kitten.png --out kitten_64x32.bmp -s format bmp

# Copy to CircuitPython device
cp kitten_64x32.bmp /Volumes/CIRCUITPY/kitten.bmp
```

**Parameters:**
- `-z 32 64` - Resize to height 32, width 64 pixels
- `--out` - Output file path
- `-s format bmp` - Convert to BMP format

The code uses `adafruit_imageload` to load BMP images, which is efficient and well-supported on CircuitPython.

## USB Connection

The Pi or Mac sends data to `usb_cdc.data` (not the console port).

## Status

The Matrix Portal M4 will print frame counts to the USB serial console to show it's receiving data.

## Troubleshooting

### circup not found
- Make sure Python 3.9 or higher is installed
- Try `pip3 install --user circup` instead
- Verify with `circup --version`

### circup can't find CIRCUITPY drive
- Make sure the Matrix Portal M4 is connected via USB
- Check that the CIRCUITPY drive is mounted
- On some systems, manually specify path: `circup --path /path/to/CIRCUITPY install adafruit_display_text`

### Library installation fails
- Update circup: `pip install --upgrade circup`
- Check CircuitPython version compatibility
- Try manual installation from https://circuitpython.org/libraries
