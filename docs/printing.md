# Printing Feature

## Overview

The printing feature generates a PDF after each snapshot capture, containing:

1. **LED Matrix Preview** — rendered with the current LED mode (circles, squares, gaussian, etc.), scaled to fill the page width
2. **Original Camera Capture** — full-resolution image from the camera, scaled to page width
3. **Thumbnail** — aspect-ratio-preserving blocky upscale of the matrix snapshot (longest side = 2")
4. **Pixel-to-pixel BMPs** — both landscape (64x32) and portrait (32x64) at native resolution, side by side
5. **Timestamp** — ISO 8601 and human-readable local time, centred at the bottom

The PDF is US Letter (8.5" x 11") at 300 DPI.

## Files Generated Per Snapshot

| File | Pattern | Description |
|------|---------|-------------|
| Viewer BMP | `snapshot_YYYYMMDD_HHMMSS.bmp` | Properly oriented for PC viewing |
| Original PNG | `snapshot_YYYYMMDD_HHMMSS_original.png` | Full-resolution camera capture |
| PDF | `snapshot_YYYYMMDD_HHMMSS.pdf` | Print-ready composite page |
| Debug raw BMP | `snapshot_YYYYMMDD_HHMMSS_raw.bmp` | Raw 64x32 frame (debug mode only) |
| Debug RGB565 | `snapshot_YYYYMMDD_HHMMSS_rgb565.bin` | Raw binary data (debug mode only) |

All snapshot files are excluded from git via `.gitignore` patterns: `snapshot_*.bmp`, `snapshot_*.png`, `snapshot_*.pdf`, `snapshot_*.bin`.

## CLI Flags

- `--no-save` — Disables all snapshot saving to disk. The countdown still runs but nothing is written.

## Architecture

### Utils Library (`ledportal-utils`)

`export_pdf()` in `utils/src/ledportal_utils/snapshot.py` is the core function. It:
- Accepts a snapshot BMP path and optional original camera image path
- Renders the LED preview using `_render_led_array()` with the specified `LedMode`
- Composes all elements on a US Letter canvas with 0.5" margins
- Saves via Pillow's PDF output (no external dependencies)

### Pro Version Integration

`SnapshotManager.save()` in `pro/src/ledportal_pro/ui/snapshot.py`:
- Accepts `render_algorithm` and `led_size_pct` from the main loop
- Maps `PreviewAlgorithm` + `led_size_pct` to the closest `LedMode` via `_resolve_led_mode()`
- Saves the original camera frame as PNG, then calls `export_pdf()`
- Returns a 4-tuple: `(snapshot_path, debug_path, rgb565_path, pdf_path)`

## Cross-Platform Printing (V2 Plan)

### macOS and Linux (CUPS)

Both platforms use CUPS. The `lpr` command is always available and prints silently:

```bash
# Print to default printer
lpr snapshot.pdf

# Print to specific printer with 4x6 photo paper
lpr -P "Canon_SELPHY" -o media=Custom.4x6in -o fit-to-page -o media-type=GlossyPaper snapshot.pdf

# Discover printer options
lpoptions -p "PrinterName" -l
```

Key CUPS options:
- `-o media=Custom.4x6in` — paper size (or `media=4x6` if PPD defines it)
- `-o fit-to-page` — scale content to fit media
- `-o media-type=GlossyPaper` — paper type (driver-dependent)
- `-o orientation-requested=3` — landscape
- `-o print-quality=5` — high quality
- `-o StpFullBleed=True` — borderless (driver-dependent)

Python: `subprocess.run(["lpr", "-o", "media=Custom.4x6in", "-o", "fit-to-page", pdf_path])`

### Windows

No single clean solution. Options ranked by preference:

1. **SumatraPDF CLI** (recommended) — free, ~6MB, truly silent:
   ```
   SumatraPDF.exe -silent -print-to-default snapshot.pdf
   SumatraPDF.exe -silent -print-to "Printer Name" snapshot.pdf
   ```

2. **ShellExecute via pywin32** — uses system default PDF reader:
   ```python
   win32api.ShellExecute(0, "print", pdf_path, f'/d:"{printer}"', ".", 0)
   ```
   Requires a PDF reader installed. No control over page size/scaling.

3. **win32print + PIL** — print images directly to printer device context. Full control over scaling and placement but ~50 lines of code. Requires `pywin32`.

4. **GhostScript** — `gswin64c.exe -sDEVICE=mswinpr2 -sOutputFile="\\spool\PrinterName" file.pdf`. Heavy (~50MB install).

### Recommended V2 Strategy

Start from the PDF on disk (already generated), then platform-dispatch:
- macOS/Linux: `subprocess.run(["lpr", ...options..., pdf_path])`
- Windows: `subprocess.run(["SumatraPDF.exe", "-silent", "-print-to-default", pdf_path])`

Alternative: start from the PIL Image in memory, save to temp PDF, print, clean up. This avoids requiring the PDF to persist on disk (relevant when `--no-save` is active but printing is desired).

### Photo Printer Considerations (4x6)

- Paper size options are driver-dependent — use `lpoptions -l` to discover
- Borderless printing varies by driver (look for `StpFullBleed`, `Borderless`, etc.)
- For a dedicated photobooth, configure the printer defaults once and use `lpr` with minimal options
- The PDF page size may need to change from US Letter to 4x6 for direct photo printing (future `export_pdf` parameter)

### No Cross-Platform Library

There is no well-maintained, free, pure-Python cross-platform printing library. The subprocess + platform detection approach is the standard pattern.
