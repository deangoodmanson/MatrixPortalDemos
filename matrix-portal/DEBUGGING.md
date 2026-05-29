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

## Diagnosing the EXT (A0) button

UP, DOWN, and EXT all use the same software debounce path (`digitalio.DigitalInOut`
with `Pull.UP`, wrapped in `Debouncer(pin)` with the default 10 ms interval). So if
EXT misbehaves while UP/DOWN work, the cause is almost always **hardware**, not the
debounce code:

| Symptom on EXT | Likely cause |
|---|---|
| Never registers | Broken wire, loose JST PH connector, switch stuck open, or A0 pin damaged (often from ESD or accidentally wiring red 3.3 V to GND) |
| Always registers (game thinks it's always pressed) | Wire shorted to GND, switch stuck closed, or A0 pin damaged stuck-low |
| Erratic / multiple presses per tap | Long mechanical bounce exceeding the 10 ms debounce window, or electrical noise on a long cable run |
| Works sometimes, not others | Intermittent connector contact or oxidation in the JST crimp |

### Quick diagnostic: read the raw pin

This bypasses `Debouncer` entirely and prints the raw pin state 20× per second for
about 10 seconds. Press and release the clicker while it runs:

```bash
uv tool run mpremote connect /dev/cu.usbmodem2101 exec "
import board, digitalio, time
p = digitalio.DigitalInOut(board.A0)
p.switch_to_input(pull=digitalio.Pull.UP)
for _ in range(200):
    print(p.value, end='', flush=True)
    time.sleep(0.05)
"
```

Interpret the output:

| Output pattern | Verdict |
|---|---|
| All `True`, even when pressed | Open: wire / connector / switch is broken; or A0 stuck high |
| All `False`, even when released | Short: wire-to-GND, switch stuck closed, or A0 stuck low |
| Cleanly flips `True` ↔ `False` with each press/release | Hardware is fine — the issue is in the debounce / loop timing |
| Flickers between `True` and `False` while untouched | Electrical noise; consider a shorter cable, a 0.1 µF cap across the switch, or a stronger external pull-up |

You'll need to soft-reset the device after running this snippet (Ctrl-D in mpremote)
to get `code.py` running again — the snippet leaves `A0` claimed by its own
`DigitalInOut`, which would conflict with `code.py`'s own claim on next launch.

### If the pin reads cleanly but the game still misses presses

The 10 ms debounce window may be too aggressive for the clicker's mechanical bounce.
A bounce longer than 10 ms shows up as a single confirmed press followed by
spurious "rose / fell" pairs, sometimes leading to no detection at all. Try
increasing the interval:

```python
ext_button = Debouncer(_pin_ext, interval=0.02)   # 20 ms instead of 10
```

Tuning above ~30 ms starts to feel noticeably laggy in gameplay; below 10 ms makes
bounce-induced double-presses likely. 15–20 ms is a reasonable range for a noisy
external clicker.

---

## Screen brightness on RGBMatrix (known limitation)

**TL;DR: `display.brightness` and `matrix.brightness` are silently ignored on the
Matrix Portal M4 / CircuitPython 10. The matrix always runs at full brightness.**
The `BRIGHTNESS` value in `settings.toml` exists but has no observable effect.

### What we observed

Both attributes exist on the relevant objects:

- `framebufferio.FramebufferDisplay.brightness` (set via `display.brightness = x`)
- `rgbmatrix.RGBMatrix.brightness` (set via `matrix.brightness = x`)

Writes don't raise. They're accepted, then silently discarded — read-back always
returns `1.0` regardless of what was just written. The LED output stays at full
intensity. This is true for both the boot-time assignment in `code.py` and any
runtime write attempt.

### Diagnostic — confirm on your hardware

Make sure no other mpremote session is holding the port, then:

```bash
uv tool run mpremote connect /dev/cu.usbmodem<lower-number> exec "
import board, rgbmatrix, framebufferio, displayio
displayio.release_displays()
m = rgbmatrix.RGBMatrix(width=64, height=32, bit_depth=6,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)
d = framebufferio.FramebufferDisplay(m)
print('matrix.brightness =', m.brightness)
print('display.brightness =', d.brightness)
m.brightness = 0.3
print('after m.brightness = 0.3, read back:', m.brightness)
import time; time.sleep(3)
"
```

If the read-back after the write is `1.0` and the LEDs don't visibly dim during the
3-second pause, the property is a no-op on your device.

### Why this happens

`brightness` is part of the displayio API contract — for displays with a backlight
(LCDs, OLEDs), the property modulates a PWM channel that drives the backlight LED.
RGB LED matrices don't have a backlight; their "brightness" would have to come from
shortening the OE (output enable) duty cycle during the BCM refresh. On CircuitPython
10 / Matrix Portal M4 that wiring isn't implemented, so the property is a stub.

### Workarounds

Pick one based on need:

1. **Live with it.** This is the default. Document expectations and move on. Some
   rooms are bright enough that full brightness is fine; others are not.
2. **Lower the `bit_depth`** in the `RGBMatrix(...)` constructor. This isn't a
   brightness control — it reduces color depth — but it does change the perceived
   intensity of mid-tones. Trade-off: fewer colors, faster refresh.
3. **Software brightness scaling.** Scale RGB565 values (camera frames) or palette
   entries (game) by a brightness factor before they hit the bitmap. Uses CPU but
   actually works.  For camera frames specifically, modify `display_frame` in
   `image_display.py` to multiply each pixel's R/G/B channels before blitting; a
   small per-channel lookup table keeps it cheap.
4. **Hardware approach (advanced).** Drive the OE pin via an external NPN/MOSFET
   PWM circuit. Out of scope for this project.

The `BRIGHTNESS` key in `settings.toml` is preserved as documentation of intent —
if CircuitPython implements RGB matrix brightness in a later release, the existing
boot-time assignment in `code.py` will start working with no other code changes.

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
