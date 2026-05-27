# Matrix Portal M4 Firmware

CircuitPython firmware for the Adafruit Matrix Portal M4. Displays a live USB camera mirror, a photo slideshow, and a built-in Silly Bird game on a 64×32 RGB LED matrix.

---

## Quick Start

### 1. Install CircuitPython libraries

Use `uv` to install `circup`, then install the required libraries onto the device:

```bash
uv tool install circup
circup install adafruit_display_text adafruit_imageload adafruit_debouncer
```

### 2. Deploy firmware

```bash
cd matrix-portal
bash deploy.sh
```

`deploy.sh` stamps the current git commit hash into `version.py` on the device and copies all firmware files. The device reboots automatically.

### 3. Verify what's running

Check the serial console on boot:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101
```

You'll see:

```
Matrix Portal M4 — mode: both  build: abc1234
```

Or query the build hash directly:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101 exec "from version import BUILD; print(BUILD)"
```

---

## Configuration (`settings.toml`)

| Key | Values | Default |
|-----|--------|---------|
| `MODE` | `"both"` · `"silly_bird"` · `"image_display"` | `"both"` |
| `BRIGHTNESS` | `"0.0"` – `"1.0"` (string, not float) | `"0.75"` |

> **Note:** CircuitPython 10's TOML parser rejects float literals. Always quote decimal values: `BRIGHTNESS = "0.75"` not `BRIGHTNESS = 0.75`.

---

## Hardware Setup

Connect the 64×32 RGB LED matrix to the Matrix Portal M4 via the HUB75 connector.

### External A0 Clicker (optional but recommended for Silly Bird)

Wire a momentary switch between the **A0** and **GND** pads on the bottom edge of the board — the two outer pins of the JST PH 3-pin connector next to the 5V screw terminal. Leave the middle (3.3 V) pin unconnected. No external resistor needed; the internal pull-up is enabled in firmware.

---

## Navigation

The device has three buttons: **UP**, **DOWN**, and **A0** (external clicker).

### Hub screen (startup)

```
USB:MIRROR   — camera mirror starts automatically when a PC connects
UP:PHOTOS    — enter photo slideshow mode
DN:BIRD      — enter Silly Bird game mode
```

### Photo mode (UP from hub)

| Button | Action |
|--------|--------|
| **UP** | Cycle: kitten → dog → bird hint → kitten … |
| **EXT** | Return to hub |

### Game mode (DOWN from hub)

| Button | Action |
|--------|--------|
| **EXT / A0** | Flap · start game in current orientation |
| **UP** | Switch to landscape (wide) and start |
| **DOWN** | Switch to portrait (tall) and start |
| **UP + DOWN held** | Quit confirm screen |

Orientation is remembered between rounds. Portrait mode rotates the game 90° CW — hold the device with the 64-pixel axis vertical, USB at the bottom.

**Exit game mode:** hold UP + DOWN → "QUIT?" screen → press UP or DOWN to return to hub (EXT resumes play).

---

## Silly Bird — Game Flow

```
→ Ready screen (game scene, bird waiting)
→ first input starts the round
→ OOF! (red overlay on crash frame) → click → Stats → click → Ready
```

Stats (score, best, runs) are kept in RAM for the session. Nothing is written to the device filesystem.

### Customising the game

Open `silly_bird.py` — the top of the file has two clearly labelled sections:

- **`# ── GAME FEEL`** — `GRAVITY`, `FLAP_POWER`, `PIPE_GAP`, `START_SPEED`, etc. Each constant has an inline comment explaining what bigger/smaller does.
- **`# ── COLORS`** — `COLOR_SKY`, `COLOR_PIPE`, `COLOR_BIRD`, etc. as `0xRRGGBB` hex values. Find codes at [htmlcolorcodes.com](https://htmlcolorcodes.com).

---

## Deploying Individual Files

If you only changed one file, copy it directly — no need to run `deploy.sh`:

```bash
cp silly_bird.py /Volumes/CIRCUITPY/silly_bird.py
```

The device auto-reboots when any file on CIRCUITPY changes.

> **After `deploy.sh`**, `version.py` on the device will reflect the stamped hash. If you copy files individually the build hash stays at the last full deploy — run `deploy.sh` again to re-stamp.

---

## Converting Images for the Slideshow

```bash
# Resize and convert any image to 64×32 BMP (macOS built-in)
sips -z 32 64 input.png --out output.bmp -s format bmp

# Copy to device
cp output.bmp /Volumes/CIRCUITPY/kitten.bmp   # or dog.bmp
```

---

## Required CircuitPython Libraries

Installed via `circup install` (see Quick Start):

| Library | Purpose |
|---------|---------|
| `adafruit_display_text` | On-matrix text labels |
| `adafruit_imageload` | BMP photo loading |
| `adafruit_debouncer` | Clean button edge detection |

Built-in to CircuitPython (no install needed): `rgbmatrix`, `framebufferio`, `displayio`, `usb_cdc`, `terminalio`.

---

## Troubleshooting

See [DEBUGGING.md](DEBUGGING.md) for a full guide covering:

- Finding serial ports (`ls /dev/cu.usbmodem*`)
- Reading the console with `mpremote`
- The CircuitPython TOML float bug
- Safe mode, port conflicts, and clean-boot verification
