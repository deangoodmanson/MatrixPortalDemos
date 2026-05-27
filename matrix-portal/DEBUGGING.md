# Debugging the Matrix Portal M4

This guide covers diagnosing problems with the CircuitPython firmware running on the Matrix Portal M4.

## Prerequisites

Install `mpremote` via uv (required — do not use pip):

```bash
uv tool install mpremote
```

## Finding Serial Ports

When the Matrix Portal is connected via USB, it exposes **two CDC serial ports** when both console and data are enabled in `boot.py` (`usb_cdc.enable(console=True, data=True)`):

| Port | Purpose |
|------|---------|
| Lower-numbered (e.g. `/dev/cu.usbmodem2101`) | REPL console — use for debugging |
| Higher-numbered (e.g. `/dev/cu.usbmodem2103`) | Data port — used by the host to stream frames |

List available ports:

```bash
# macOS / Linux
ls /dev/cu.usbmodem*        # macOS
ls /dev/ttyACM*             # Linux

# Or use mpremote to list all candidates
uv tool run mpremote devs
```

## Reading the Serial Console

The simplest way to see what the device is printing:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101
```

Press **Ctrl-C** inside the mpremote session to interrupt running code and get a REPL prompt. Press **Ctrl-D** to soft-reset the device.

To run a one-liner without entering the REPL interactively:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101 exec "print('hello')"
```

## Common Symptoms and Fixes

### Blank Screen / No Display

The most likely causes, in order:

#### 1. settings.toml float literal (TOML parse error)

**Symptom**: Device boots, CIRCUITPY drive mounts, but the screen stays dark. The mpremote console shows a traceback like:

```
ValueError: invalid syntax for integer with base 0
```

**Root cause**: CircuitPython 10's TOML parser does not accept float literals. A value like `BRIGHTNESS = 0.75` causes a parse error. The app never starts.

**Fix**: Quote all decimal values as strings:

```toml
# Wrong — causes ValueError
BRIGHTNESS = 0.75

# Correct — read with float(os.getenv("BRIGHTNESS", "0.75"))
BRIGHTNESS = "0.75"
```

After fixing `settings.toml`, copy it to the device:

```bash
cp matrix-portal/settings.toml /Volumes/CIRCUITPY/settings.toml
```

The device auto-reboots when the file changes.

#### 2. Serial port held by another process

**Symptom**: `mpremote` reports `failed to access /dev/cu.usbmodem2101 (it may be in use by another program)`.

**Fix**:

```bash
lsof /dev/cu.usbmodem2101      # find the PID
kill <PID>
```

#### 3. Python traceback during startup

**Symptom**: Screen dark, and `mpremote` shows a Python exception.

**Fix**: Read the full traceback to identify the file and line number. Edit the relevant file in `matrix-portal/`, copy it to CIRCUITPY, and the device will auto-reboot.

### `mpremote` Cannot Enter Raw REPL

**Symptom**: `TransportError: could not enter raw repl`

This usually means the device is actively running code and not responding to the REPL interrupt sequence. Try:

1. **Soft reset**: press **Ctrl-D** in an open mpremote session.
2. **Hard reset**: disconnect and reconnect the USB cable, then reconnect mpremote.
3. **Safe mode**: hold the Reset button for 1 second and release when the NeoPixel turns yellow — the device boots into safe mode (no `code.py`), giving you a clean REPL.

### Port In Use / No Ports Visible

If `ls /dev/cu.usbmodem*` returns nothing:

- Try a different USB cable (data cable, not charge-only).
- Try a different USB port.
- Check Device Manager (Windows) or System Information → USB (macOS) for the device.
- If previously connected, the OS may need a moment — wait 5–10 s after plugging in.

## Deploying Code to the Device

The CIRCUITPY drive mounts as a USB mass-storage device. Copy files directly:

```bash
# Copy a single file
cp matrix-portal/silly_bird.py /Volumes/CIRCUITPY/silly_bird.py

# Copy all firmware files (excluding dev-only files)
cp matrix-portal/code.py          /Volumes/CIRCUITPY/code.py
cp matrix-portal/boot.py          /Volumes/CIRCUITPY/boot.py
cp matrix-portal/image_display.py /Volumes/CIRCUITPY/image_display.py
cp matrix-portal/silly_bird.py    /Volumes/CIRCUITPY/silly_bird.py
cp matrix-portal/settings.toml    /Volumes/CIRCUITPY/settings.toml
```

The device automatically soft-resets and runs `code.py` whenever a file on CIRCUITPY changes.

## Verifying a Clean Boot

After deploying, check the console for a clean startup sequence:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101
```

Expected output on a healthy boot:

```
Matrix Portal M4 — mode: both
```

If you see a traceback instead, the error message and line number will point you to the problem.

## Checking File System Usage

The Matrix Portal M4 has very limited flash. To avoid filesystem writes from application code (e.g. old stat files), check for unexpected files:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101 exec "import os; print(os.listdir('/'))"
```

Remove unwanted files:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101 exec "import os; os.remove('/silly_bird_stats.txt')"
```

Or delete from the mounted CIRCUITPY drive:

```bash
rm /Volumes/CIRCUITPY/silly_bird_stats.txt
```

## CircuitPython Version

To confirm the running version:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101 exec "import sys; print(sys.version)"
```

This project targets **CircuitPython 10.0.x**.

## settings.toml Type Rules

CircuitPython's TOML parser only supports these value types:

| Type | Example |
|------|---------|
| String | `KEY = "value"` |
| Integer | `KEY = 42` |
| Boolean | `KEY = true` |
| **Float — NOT supported** | `KEY = 0.75` ← causes `ValueError` |

Always pass decimals as quoted strings and parse them with `float(os.getenv("KEY", "default"))` in `code.py`.
