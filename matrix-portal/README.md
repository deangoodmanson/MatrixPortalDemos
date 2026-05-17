# Matrix Portal M4 Frame Display

CircuitPython application for Adafruit Matrix Portal M4 to receive and display camera frames, with a built-in Silly Bird game.

## Setup

1. Install CircuitPython on your Adafruit Matrix Portal M4
2. Install `circup` on your computer: `pip install circup`
3. Copy both `boot.py` and `code.py` to the CIRCUITPY drive
4. Install required libraries: `circup install adafruit_display_text adafruit_debouncer`
5. Reset the Matrix Portal M4 for boot.py to take effect

**Important:** The `boot.py` file enables the USB data port and grants Python write access to the filesystem (for stats). By default your computer cannot write to CIRCUITPY while the device is running — **hold the DOWN button during boot** to temporarily restore USB write access for code deployment.

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
circup install adafruit_display_text adafruit_imageload adafruit_debouncer
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
- `adafruit_debouncer.mpy` (hardware button debouncing)

### Built-in Libraries

The following are built-in to CircuitPython (no installation needed):
- `rgbmatrix`
- `framebufferio`
- `displayio`
- `usb_cdc`
- `terminalio`

## Hardware Setup

Connect the 32x64 RGB LED matrix to the Matrix Portal M4 using the HUB75 connector.

### External Snap Button (optional)

Wire a momentary switch between the **A0** and **GND** pads on the bottom edge of the board. No resistor needed — the internal pull-up is enabled. Do not connect to the 3.3 V pad between them.

## Button Controls

All three buttons use hardware debouncing (`adafruit_debouncer`) for clean edge detection.

| Button | Action |
|--------|--------|
| **UP** | Cycle through: kitten image → dog image → "Push DOWN for Silly Bird" hint |
| **DOWN** | Launch Silly Bird game |
| **A0 (external)** | Send `SNAP` command to the host over USB console |

## Silly Bird

Press **DOWN** to launch the built-in Silly Bird game (a Flappy Bird clone on the 64×32 matrix).

### Silly Bird Controls

| Button | Action |
|--------|--------|
| **UP**, **DOWN**, or **A0** | Flap (all three work identically) |
| **DOWN** (title screen) | Exit back to camera / waiting screen |
| **UP + DOWN** (held simultaneously, in-game) | Quit game immediately |

### Title Screen
- Press **UP** or **A0** to start
- Press **DOWN** to exit back to the main display

### Gameplay
- Guide the bird through gaps in the green pipes
- Each pipe pair cleared scores **+1**
- Pipe speed increases with score
- Hitting a pipe, the ground, or the ceiling ends the run

### Visual Effects
- Wing pixel animates based on vertical velocity (up when climbing, down when falling)
- Consecutive climbing flaps produce smoke puffs behind the bird
- Every 3rd consecutive climbing flap produces a fire puff instead

### Game Over & Stats

When the bird collides with a pipe or the ground:

1. **OOF!** screen appears with your score — held for 1.5 seconds
2. Label changes to **TAP!** — press any button to continue
3. **Stats screen** appears showing:
   - `SCORE` — points scored this run
   - `BEST` — all-time high score
   - `RUNS` — total games played
   - Header shows **NEW BEST!** (orange) if you beat the record, otherwise **- STATS -** (gold)
4. Press any button to return to the title screen

Stats are saved to `/silly_bird_stats.txt` on the CIRCUITPY drive and persist across power cycles.

## How It Works

1. On startup, displays "WAITING FOR USB" message in green
2. Matrix Portal M4 exposes a USB CDC (serial) data port
3. Receives RGB565 frame data (4,096 bytes per frame)
4. Switches to frame display when first frame arrives
5. Updates the LED matrix at up to 30 FPS

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

### Silly Bird doesn't respond to button presses
- Make sure `adafruit_debouncer` is installed (`circup install adafruit_debouncer`)
- Check the REPL for an `ImportError` on startup

### Stats not saving ("Stats save failed" in REPL)
- The filesystem is in USB write mode — hold **DOWN** during boot was likely active when the device last reset
- Reset the board without holding DOWN so `boot.py` can remount the filesystem for Python writes
- Confirm by checking the REPL: if `storage.remount` ran, there will be no write errors
