# Waveshare ESP32-C6 — CircuitPython Setup

*2026-10-09*

## Board overview

The Waveshare ESP32-C6 uses the chip's native USB (no external USB-to-UART bridge), so it enumerates directly under Espressif's own USB vendor ID.

| Property | Value |
| --- | --- |
| USB VID:PID | `0x303A:0x1001` |
| Serial interface | `USB Serial Device` (MI_00) — appeared as **COM3** |
| Debug interface | `USB JTAG/serial debug unit` (MI_02) — WinUsb, for OpenOCD / on-chip debugging |

A first cable that showed up only as power (no data lines) produced no USB serial enumeration at all. A proper data-capable USB-C cable is required for flashing and the REPL.

## Display

| Property | Value |
| --- | --- |
| Panel | 1.47" TFT, ST7789 controller |
| Native resolution | 172 × 320 (portrait) |
| Landscape resolution | 320 × 172 |
| Colors | 262K (18-bit) |

### Resolution vs. Matrix Portal (64×32 LED matrix)

| | Matrix Portal | Waveshare ESP32-C6 (landscape) |
| --- | --- | --- |
| Resolution | 64 × 32 | 320 × 172 |
| Aspect ratio | 2.00:1 | 1.86:1 |
| Pixel count | 2,048 | 55,040 (~27×) |

The aspect ratios are close but not identical. **Decision for the Silly Bird port:**
keep the existing 64×32 logical game bitmap unchanged and upscale it 5× onto the
320×172 panel — 64×5=320 fills the width exactly, 32×5=160 leaves a 6px letterbox
bar top and bottom (160+6+6=172). This is an integer scale (no blur/distortion) and
reuses `silly_bird.py`'s drawing code (`box()`, `draw_bird()`, `draw_pipe()`, etc.)
as-is. `displayio.TileGrid` supports a `scale` attribute that does this upscaling
for free — no manual pixel-doubling code needed; just set `tile_grid.scale = 5` and
offset `y = 6` when placing it in the group.

### Pin mapping — CONFIRMED live from the device

Read directly over the serial REPL (COM3, 115200 baud, `import board; print(dir(board))`)
on 2026-10-10, CircuitPython 10.3.1:

```
>>> dir(board)
['A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'BUTTON', 'DISPLAY', 'I2C',
 'IO0', 'IO1', 'IO2', 'IO3', 'IO4', 'IO5', 'IO6', 'IO7', 'IO8', 'IO9',
 'IO16', 'IO17', 'IO18', 'IO19', 'IO20', 'IO23',
 'MISO', 'NEOPIXEL', 'RX', 'SCL', 'SDA', 'SD_CS', 'SPI',
 'TFT_BACKLIGHT', 'TFT_CS', 'TFT_DC', 'TFT_RESET', 'TX', 'UART', 'board_id']
```

Key findings:

- **`board.DISPLAY` already exists and works out of the box.** CircuitPython
  auto-initializes the ST7789 as a `BusDisplay` using `TFT_CS`/`TFT_DC`/`TFT_RESET`/
  `TFT_BACKLIGHT` + the `SPI` bus — **no manual `adafruit_st7789` driver setup or
  pin wiring is needed**, unlike the Matrix Portal's manual `rgbmatrix.RGBMatrix(...)`
  construction. Confirmed: `board.DISPLAY.width, .height, .rotation` → `172 320 0`
  (native portrait; set `.rotation = 90` or `270` for the 320×172 landscape used by
  the Silly Bird port plan above).
- **`board.BUTTON` is the only user button exposed, and it is `board.IO9`**
  (`print(board.IO9)` also prints `board.BUTTON` — same pin, two names). This is the
  classic ESP32 strapping/BOOT button. The schematic's second button (`Key2`) is not
  exposed as a separate `board.*` name in this CircuitPython build — it may be the
  hardware RESET button instead, which CircuitPython can't read as a GPIO.
- **Only one on-board button exists for gameplay**, vs. the Matrix Portal's three
  inputs (`button_up`, `button_down`, external A0 flap button). Silly Bird's mode
  picker and flap controls need either a 1-button remap (e.g. long-press vs.
  short-press to distinguish flap from mode-select) or an external button wired to a
  free GPIO (`IO0`, `IO1`, `IO16-20`, `IO23`, or `A0-A5`), mirroring the Matrix
  Portal's A0 JST approach.
- `board.NEOPIXEL` (onboard RGB LED) and `board.SD_CS` (microSD slot) are also
  available but not needed for the port.

### No CIRCUITPY mass-storage drive on this board/port combo

Unlike Matrix Portal (and most CircuitPython boards), this board's native USB does
**not** expose a `CIRCUITPY` drive letter to Windows — confirmed via
`Get-Volume`/`Get-Disk`/`Get-Partition` (PowerShell): no removable volume appears at
all, only the fixed internal disk. This matches the earlier finding that USB only
enumerates two interfaces (`USB Serial Device` MI_00, `USB JTAG/serial debug unit`
MI_02) — no mass-storage (MSC) interface. The filesystem is there and mounted
(`storage.getmount('/')` → `<VfsFat>`, `os.listdir('/')` →
`['sd', 'settings.toml', 'code.py', 'lib', 'boot_out.txt']`), it's just not visible
to the host as a drive.

### Display corruption — CONFIRMED not a rotation/offset bug, likely hardware

While deploying over the serial REPL with `display.rotation = 90` active (set by
`code.py` for the landscape Silly Bird layout), a vertical band near the left edge of
the panel showed speckled/garbled pixels while the rest rendered cleanly (observed via
photo, 2026-10-10). Ran a controlled comparison: set `display.rotation = 0` (native
portrait) directly over the REPL and re-photographed — **the same vertical band of
corruption was still present**, in the same relative panel position. This rules out a
rotation-dependent row/column-start offset bug (which would disappear at the native
rotation); the corruption is independent of `display.rotation`.

A consistent narrow vertical band (not random full-screen speckle) is a typical
signature of a loose/damaged FPC ribbon connector between the display panel and the
board, or physical damage to the panel itself — not something fixable in software.
Next diagnostic step: visually check (or gently reseat, if accessible) the FPC
connector before concluding the panel itself is defective.

**Deployment method for this board:** push files over the serial REPL (COM3,
115200 baud) rather than drag-and-drop onto a `CIRCUITPY` drive. A Python script
using `pyserial` (run via `uv run --with pyserial python <script>.py`) can open a
raw-REPL `exec()` session, open a file in write mode on the device, and write
content in chunks — this is the same approach tools like `ampy`/`mpremote` use
under the hood. `mpremote` or `circup` (if installable for this board) may offer a
cleaner CLI alternative to a hand-rolled script; worth checking before writing more
custom tooling.

## Installing CircuitPython

**Status: done.** CircuitPython 10.3.1 is installed via the browser-based web installer.

Board page: [ESP32-C6 1.47inch Display Development Board — Waveshare](https://circuitpython.org/board/waveshare_esp32_c6_lcd_1_47/) (check this page for the exact Waveshare model if it differs — Waveshare has more than one ESP32-C6 variant).

### What was done

- Opened the circuitpython.org board page in Chrome (Web Serial requires Chrome/Edge — it does not work in Firefox or Safari)
- Used the in-browser installer against **COM3**, which erased and flashed the board directly

### Manual esptool fallback (for reference / reflashing)

If the web installer isn't available, flash the `.bin` from the board page manually:

```
pip install esptool
esptool.py --chip esp32c6 --port COM3 erase_flash
esptool.py --chip esp32c6 --port COM3 write_flash -z 0x0 <downloaded-firmware>.bin
```

## Troubleshooting

- **No COM port appears at all:** the USB cable is likely power-only (no data lines). Swap to a known data-capable USB-C cable — this happened on first attempt with this board.
- **esptool/installer can't connect to enter download mode:** hold **BOOT**, tap **RESET**, then release **BOOT**. The ESP32-C6's native USB doesn't always auto-reset into bootloader mode the way boards with a dedicated USB-UART chip do.
- **Web installer doesn't detect the board:** confirm you're using Chrome or Edge — Web Serial isn't supported in Firefox or Safari.

## Next steps

- Board should now present a `CIRCUITPY` USB drive. Drop code into `code.py` at its root to run it.
- Install libraries by copying `.mpy` files from the [CircuitPython library bundle](https://circuitpython.org/libraries) into `CIRCUITPY/lib/`.
- Edit with any text editor, [Mu](https://codewith.mu/), or the [Adafruit web workflow](https://learn.adafruit.com/getting-started-with-web-workflow-using-circuitpython) if the board supports it.
- Serial console / REPL: connect to **COM3** at 115200 baud (e.g. PuTTY, `screen`, or Mu's serial pane) for `print()` output and live REPL access.

### Sources

- [Waveshare ESP32-C6 1.47" board — circuitpython.org](https://circuitpython.org/board/waveshare_esp32_c6_lcd_1_47/)
- [Installing CircuitPython on ESP32 — Adafruit Learn](https://learn.adafruit.com/circuitpython-with-esp32-quick-start/installing-circuitpython)
- [esptool docs — ESP32-C6](https://docs.espressif.com/projects/esptool/en/latest/esp32c6/index.html)
- [ESP32-C6-LCD-1.47 product page — Waveshare](https://www.waveshare.com/esp32-c6-lcd-1.47.htm)
- [ESP32-C6-LCD-1.47 schematic PDF — Waveshare](https://files.waveshare.com/wiki/ESP32-C6-LCD-1.47/ESP32-C6-LCD-1.47_schemetics.pdf)
- [ESP32-C6-LCD-1.47 docs — docs.waveshare.com](https://docs.waveshare.com/ESP32-C6-LCD-1.47)
- [1.47inch Touch LCD wiki (ESP32-S3 pin mapping — different board, for reference only)](https://waveshare.com/wiki/1.47inch_Touch_LCD)
