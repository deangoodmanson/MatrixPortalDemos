# LED Portal MacroPad Key Mapping

Macro configuration files for the [Adafruit MacroPad RP2040](https://www.adafruit.com/product/5128)
using the [MACROPAD Hotkeys](https://learn.adafruit.com/macropad-hotkeys) app to control
[MatrixPortalDemos](https://github.com/deangoodmanson/MatrixPortalDemos) .

## Setup

1. Install CircuitPython and the Adafruit MACROPAD Hotkeys `code.py` on your MacroPad per the
   [guide](https://learn.adafruit.com/macropad-hotkeys/project-code).
2. Copy the page files (`0_processing.py` through `4_system.py`) into `CIRCUITPY/macros/`.
3. Run `camera_feed.py` on the host machine.
4. Twist the encoder to select a page, press keys to send commands.

## Encoder

| Input | Action |
|---|---|
| Twist | Cycle through pages |
| Click | Snapshot (`Space`) — works on every page |

## Pages

Pages load in filename order. The OLED header shows the current page name.

### Page 0 — Processing

Controls how the camera frame is mapped to the 64×32 matrix.

| Key | Label | Command |
|---|---|---|
| 0 | CROP | `c` — center crop (default) |
| 1 | STRCH | `s` — stretch to fill |
| 2 | FIT | `f` — fit with letterbox |

### Page 1 — Effects

Visual effects applied to the frame before transmission.

| Key | Label | Command |
|---|---|---|
| 0 | B&W | `b` — toggle black & white |
| 1 | MIRRR | `m` — toggle mirror |
| 2 | ZOOM | `z` — cycle zoom (100→75→50→25→100%) |
| 3 | ALGO | `o` — cycle render algorithm (Gaussian Diffused→Squares→Circles→Gaussian Raw) |
| 4 | SZ+ | `=` — increase LED size (Circles mode only) |
| 5 | SZ- | `-` — decrease LED size (Circles mode only) |

### Page 2 — Actions

One-shot capture commands.

| Key | Label | Command |
|---|---|---|
| 0 | SNAP | `Space` — take snapshot |
| 1 | AVTR | `v` — avatar capture mode |

### Page 3 — Orientation

Display orientation of the LED matrix.

| Key | Label | Command |
|---|---|---|
| 0 | LNDSCP | `l` — landscape (default) |
| 1 | PORTR | `p` — portrait |

### Page 4 — System

Diagnostic and control commands.

| Key | Label | Command |
|---|---|---|
| 0 | DEBUG | `d` — toggle debug overlay |
| 1 | PREVW | `w` — toggle preview window on host |
| 2 | DEMO | `x` — toggle demo mode (auto-cycles all features) |
| 3 | HELP | `h` — print help + current settings to console |
| 4 | RESET | `r` — reset to defaults |
| 5 | MNDMO | `Shift+X` — start manual demo mode |
| 6 | < PRV | `,` — previous demo step |
| 7 | NXT > | `.` — next demo step |

## Repeaters (bottom row, every page)

Keys 9–11 are the same on all pages so critical controls are always reachable
without switching pages.

| Key | Label | Command |
|---|---|---|
| 9 | RESET | `r` — reset to defaults |
| 10 | TX | `t` — toggle transmission to matrix |
| 11 | QUIT | `q` — quit |

## Color Legend

| Color | Group |
|---|---|
| Cyan | Processing modes |
| Magenta / Purple | Effects |
| Green | Actions |
| Yellow | Orientation |
| Teal / Orange | System |
| Dim white | Repeater — Reset |
| Orange | Repeater — TX |
| Red | Repeater — Quit |

## Key Reference (host-side keyboard)

Full key map from `input.py`. All commands are available from the MacroPad
except demo navigation via `>` / `<` (use `.` / `,` on the MacroPad instead).

| Key | Command |
|---|---|
| `l` | Landscape orientation |
| `p` | Portrait orientation |
| `c` | Center crop |
| `s` | Stretch |
| `f` | Fit / letterbox |
| `b` | Toggle B&W |
| `m` | Toggle mirror |
| `z` | Zoom cycle |
| `o` | Cycle render algorithm |
| `=` or `+` | LED size increase (Circles only) |
| `-` or `_` | LED size decrease (Circles only) |
| `Space` | Snapshot |
| `v` | Avatar capture |
| `x` | Toggle demo mode |
| `Shift+X` | Manual demo mode |
| `.` or `>` | Next demo step |
| `,` or `<` | Previous demo step |
| `t` | Toggle transmission |
| `d` | Toggle debug |
| `w` | Toggle preview window |
| `r` | Reset |
| `h` | Help |
| `q` | Quit |
