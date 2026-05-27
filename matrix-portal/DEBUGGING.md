# Debugging the Matrix Portal M4

This guide covers diagnosing problems with the CircuitPython firmware running on the Matrix Portal M4.

---

## Debounce Handling and Why Fast Clicks Are Missed

### What debouncing is

Physical push buttons are mechanical switches. When you press one, the metal contacts
don't make a clean single connection — they *bounce*, making and breaking contact
dozens of times in the first 5–20 ms before settling. Without software filtering, each
bounce would register as a separate "press" event.

`adafruit_debouncer.Debouncer` solves this by only confirming a state change after
the input has been stable for a configurable interval (default: **10 ms**). Transitions
shorter than that are treated as electrical noise and ignored.

### How `Debouncer` works

```python
from adafruit_debouncer import Debouncer
import digitalio

_pin = digitalio.DigitalInOut(board.A0)
_pin.switch_to_input(pull=digitalio.Pull.UP)
button = Debouncer(_pin)   # default interval = 10 ms
```

With `Pull.UP`, the pin reads:

| Physical state | Pin voltage | `button.value` |
|----------------|-------------|----------------|
| Not pressed    | 3.3 V (HIGH)| `True`         |
| Pressed        | 0 V (LOW)   | `False`        |

Each call to `button.update()` samples the pin and advances the internal state machine:

| Property       | Meaning |
|----------------|---------|
| `button.value` | Current debounced state (`False` = pressed) |
| `button.fell`  | `True` for **exactly one** `update()` call — the call that first confirms a press |
| `button.rose`  | `True` for **exactly one** `update()` call — the call that first confirms a release |

`fell` is a one-shot event. Even if the button stays held, `fell` is `False` on every
subsequent `update()`. The game uses `fell` to mean "just tapped" — not "currently held."

### The game loop timing problem

The Silly Bird game loop runs at ~20 FPS (50 ms per frame). `update()` is called
**once, at the very top of the loop**, before anything else:

```
┌─ update() called (samples pin RIGHT NOW) ──────────────────────────────────┐
│                                                                             │
│  physics 1–2 ms  │  drawing 5–10 ms  │  display.refresh() ~15 ms  │  sleep(50 ms)  │
│                                                                             │
└─────────────────────────────── ~70 ms total ───── update() called again ──→
```

During the `~70 ms` after `update()` fires, button states are **not being sampled**.
Any press that starts and ends within that window is invisible to the Debouncer
because `update()` was never called while the pin was LOW.

### When a click is missed vs. detected

**Detected** — button is still held when the next `update()` fires:

```
T=0 ms    update() → pin HIGH → fell=False
T=30 ms   button pressed (pin goes LOW)
T=70 ms   update() → pin LOW, stable for 40 ms > 10 ms → fell=True  ✓
T=90 ms   button released
```

**Missed** — press and release both happen between two `update()` calls:

```
T=0 ms    update() → pin HIGH → fell=False
T=20 ms   button pressed
T=50 ms   button released
T=70 ms   update() → pin HIGH → fell=False  ✗  (entire press happened mid-frame)
```

**Also missed** — press is too short to survive the debounce interval:

```
T=0 ms    update() → pin HIGH
T=65 ms   button pressed (pin goes LOW)
T=68 ms   button released (pin returns HIGH)  ← lasted only 3 ms, < 10 ms debounce
T=70 ms   update() → pin HIGH → never confirmed LOW → fell=False  ✗
```

In practice: **hold the button until you see or feel the response**, not just a
light tap. A press that lasts at least one full frame (~70 ms) almost always registers.

### The quit-confirm chord (UP + DOWN held together)

The "both held" gesture uses `button.value` (the current debounced state) rather than
`fell`:

```python
if not button_up.value and not button_down.value:
    # both buttons confirmed held right now
    ...
```

`value` is checked every frame regardless of whether a falling edge occurred, so
sustained holds are far more reliable than taps. The 10 ms debounce still applies,
but once confirmed the state stays `False` as long as the button is physically held.

### Making taps more reliable (trade-offs)

| Approach | Effect | Cost |
|----------|--------|------|
| Call `update()` inside the `time.sleep` at the end of the loop | Halves or quarters the blind-spot window | Slightly more complex loop |
| Reduce `FRAME_DELAY` in `silly_bird.py` (e.g. 0.05 → 0.025) | `update()` fires twice as often | Higher GC pressure; display.refresh called more often |
| Replace `fell` with manual edge detection on `value` | Can detect short presses if `update()` is called frequently enough | Requires tracking previous state per button |

The current design keeps the loop simple and the 50 ms frame is generous for normal
game play. A deliberate press (not a light fingernail tap) is virtually always
detected on the first or second frame.

---

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
