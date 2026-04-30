# Flappy Bird — Matrix Portal M4

Flappy Bird clone for the Adafruit Matrix Portal M4 on a **64×32 RGB LED matrix**.

## Installation

1. Copy `code.py` to the root of your **CIRCUITPY** drive (replaces any existing `code.py`).
2. The game starts automatically on power-up.

> **Note:** This uses CircuitPython 10 (the Matrix Portal M4 does not run MicroPython). All required libraries (`rgbmatrix`, `framebufferio`, `bitmaptools`, `adafruit_display_text`) ship with the standard CircuitPython bundle.

## Controls

| Button | Action |
|--------|--------|
| **UP** or **DOWN** | Flap (both buttons work identically) |

- **Title screen** — press either button to start
- **Playing** — press to flap upward
- **Game over** — press either button to restart

## Gameplay

- Guide the bird through gaps between the green pipes.
- Each pipe pair you clear scores **+1**.
- Pipe speed increases every point — how far can you get?
- Hitting a pipe, the ground, or the ceiling ends the run.

## Display Layout

```
┌────────────────────────────────────────────────────────────────┐  ← row 0
│  score                                          [sky]          │
│  ██ ████                  ████                                 │  ← pipes
│     ████       [bird]     ████                                 │
│                           ████  ████                           │
│                                 ████                           │
├────────────────────────────────────────────────────────────────┤  ← row 27
│                        [ground]                                │
└────────────────────────────────────────────────────────────────┘  ← row 31
  col 0                                                      col 63
```

## Technical Details

| Property | Value |
|----------|-------|
| Resolution | 64×32 pixels |
| Colour palette | 8 colours |
| Target frame rate | ~20 FPS |
| Language | CircuitPython 10 |
| Rendering | `bitmaptools.fill_region` (C-level) |
| Score font | Custom 3×5 pixel digits |
