# Printing — Photo-Booth 4×6 Output

LED Portal Pro can turn any snapshot into a printed 4×6" photo, suitable for a
photo-booth setup. This document covers what gets produced, how to enable it,
how printing works on each platform, and how to troubleshoot it.

For the snapshot pipeline as a whole (BMP, Letter PDF, debug files), see the
[Snapshot output](README.md#snapshot-output) section of the README.

---

## What gets produced

Every snapshot always writes a **BMP**. Two optional PDFs can be produced
alongside it:

| Output | Default | Size | Purpose |
|--------|---------|------|---------|
| `snapshot_<ts>.bmp` | always | 64×32 (or 32×64) | The raw image, any viewer |
| `snapshot_<ts>.pdf` | on | US Letter 8.5×11" | Multi-format contact sheet (LED preview, original photo, thumbnails, pixel-to-pixel) |
| `snapshot_<ts>_4x6.pdf` | off | 6×4" landscape | **The photo-booth print** — LED art centred on white, local timestamp lower-right |

The 4×6 PDF is rendered at 300 DPI with the page size embedded, so it prints at
true 6×4" on photo paper.

---

## Enabling printing

Three independent controls, each settable three ways:

| Setting | What it does |
|---------|--------------|
| `export_pdf` | Generate the Letter contact-sheet PDF (default **true**) |
| `export_4x6` | Generate the 4×6 PDF on disk, **without** printing (default **false**) |
| `auto_print` | Generate the 4×6 PDF **and send it to the printer** (default **false**). Implies `export_4x6`. |

### Via config YAML

```yaml
ui:
  export_pdf: true     # keep or disable the Letter contact sheet
  export_4x6: false    # save the 4×6 to disk only
  auto_print: true     # save the 4×6 AND print it
```

### Via command line (overrides config)

```bash
ledportal --auto-print            # print every snapshot's 4×6
ledportal --export-4x6            # save 4×6 to disk, don't print
ledportal --no-auto-print         # force-disable printing even if config enables it
ledportal --no-pdf                # skip the Letter contact sheet
```

### Via keyboard (at runtime)

Press **`P`** during a session to toggle auto-print on/off. The current state
shows in the `h` help screen (`Auto-print=ON/OFF`) and the snapshot output line.

---

## How printing works per platform

The print dispatch (`_dispatch_print` in `ui/snapshot.py`) routes by OS:

| Platform | `sys.platform` | Mechanism | Honors 4×6 media/orientation flags? |
|----------|----------------|-----------|--------------------------------------|
| **macOS** | `darwin` | `lpr` (CUPS) | Yes — passed as CUPS options |
| **Linux / Raspberry Pi** | `linux` | `lpr` (CUPS) | Yes — passed as CUPS options |
| **Windows** | `win32` | `os.startfile(pdf, "print")` | No — relies on the PDF's embedded page size |
| other | — | no-op (PDF still saved) | n/a |

On macOS/Linux the exact command is:

```bash
lpr -o media=Custom.4x6in -o fit-to-page -o landscape snapshot_<ts>_4x6.pdf
```

`check=False` means a print failure never crashes the app; a non-zero `lpr`
exit code prints a warning instead.

---

## Platform setup

### macOS

Works out of the box — CUPS ships with macOS. Just set your photo printer as
the default (System Settings → Printers & Scanners → right-click → Set default),
or it uses whatever the default queue is.

### Linux / Raspberry Pi

CUPS is **not** installed by default on a headless Pi. Install and configure it:

```bash
sudo apt update
sudo apt install cups
sudo usermod -aG lpadmin $USER        # allow your user to manage printers

# Add and set a default printer (USB photo printer plugged in):
lpinfo -v                              # list detected devices
sudo lpadmin -p boothprinter -E -v usb://... -m everywhere
lpoptions -d boothprinter              # make it the default

lpstat -d                              # confirm the default printer
echo test | lpr                        # smoke-test the queue
```

Once `lpstat -d` shows a default printer, `--auto-print` works identically to
macOS.

### Windows

No CUPS. Printing goes through the **default PDF handler's** print verb
(`os.startfile(pdf, "print")`), so two things must be true:

1. A program is associated with `.pdf` (Edge, Acrobat, etc. — essentially always
   the case).
2. A default printer is set (Settings → Bluetooth & devices → Printers &
   scanners → pick printer → Set as default).

**Caveat:** Windows printing does **not** receive the CUPS media/orientation
flags. The 4×6 size is taken from the page size embedded in the PDF, but the
*physical* result depends on the viewer and the printer's default tray/media.
A printer defaulting to Letter may scale or letterbox the 4×6. If sizing is
unreliable in a classroom, see the upgrade note below.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Warning: lpr exited with code N` | No default printer / CUPS not configured | `lpstat -d`; set a default with `lpoptions -d <name>` |
| "Printing not supported on platform" | Unrecognized OS | None — the 4×6 PDF is still saved; print it manually |
| Nothing prints on Windows, no error | No `.pdf` association or no default printer | Associate a PDF viewer; set a default printer |
| Prints on Letter, art tiny/letterboxed (Windows) | Viewer ignored embedded 4×6 size | Set printer default media to 4×6, or use SumatraPDF (below) |
| Prints but wrong colors/orientation | Printer driver/PPD media settings | Check the printer's own media/orientation defaults |

### Windows sizing upgrade path

If `os.startfile` printing is unreliable for 4×6 on classroom Windows machines,
the robust alternative is bundling **SumatraPDF** and calling:

```
SumatraPDF.exe -print-to-default -print-settings "paper=4x6,fit" snapshot_<ts>_4x6.pdf
```

SumatraPDF supports explicit paper-size and scaling flags that Windows' shell
print verb lacks. This adds an external binary dependency, so it's intentionally
not the default — adopt it only if real classroom hardware needs it.

---

## Photo-booth tips

- Pair with the **A0 hardware snap button** (see `config/default.yaml`) for a
  hands-free shutter: press the physical button → instant snapshot → auto-print.
- Set `auto_print: true` in your config so every shot prints without keyboard
  interaction.
- The timestamp on the 4×6 is **local wall-clock time** — recognizable as the
  time of the shot, independent of file timestamps.
