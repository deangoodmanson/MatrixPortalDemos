#!/usr/bin/env python3
"""
RGB565 Roundtrip Artifact Comparison
=====================================
Investigates why the physical LED matrix can show color artifacts that do not
appear in the BMP snapshot saved by the software.

Usage:
    cd MatrixPortalDemos
    uv run --project pro python docs/compare_rgb565.py [snapshot.bmp]

Default: uses the most recent non-raw snapshot BMP in pro/

Example output:
    Comparing: pro/snapshot_20260224_110820.bmp
    Image size: 64×32 = 2048 pixels
    Changed pixels (any channel):    1909 / 2048  (93.2%)
    Noticeably shifted (≥8 counts):     0 / 2048  (0.0%)
    Per-channel max shift: R: max=+7  G: max=+3  B: max=+7

    The diff image is nearly all black — RGB565 quantization is NOT the cause
    of visible color artifacts.  See "What causes the artifacts?" below.

-------------------------------------------------------------------------------
How this comparison works
-------------------------------------------------------------------------------

The software pipeline is:

    Camera frame (BGR, uint8)
        → resize/crop to 64×32
        → save as BMP  ← this is what you see on screen
        → convert_to_rgb565()   [RGB888 → RGB565, little-endian bytes]
        → send over USB serial
        → CircuitPython: array.array('H', bytes) + bitmaptools.arrayblit()
        → ColorConverter(Colorspace.RGB565) drives the LEDs

The BMP captures the frame BEFORE RGB565 conversion, so it stores full 8-bit
colour per channel.  The matrix only ever sees the quantized 16-bit value.

This script simulates that quantization:

    original BMP  →  to_rgb565_and_back()  →  roundtripped image
                                           →  |diff| × 4  (artifact map)

Then it saves a side-by-side 10× magnified PNG:
    Left   — original BMP   (what software saved / preview shows)
    Centre — roundtripped   (what the matrix receives after quantization)
    Right  — |diff| × 4     (where colour changed; amplified for visibility)

-------------------------------------------------------------------------------
RGB565 bit layout
-------------------------------------------------------------------------------

    RRRRR GGG GGG BBBBB
    15-11  10-5    4-0

    R: 5 bits (0-31)  — Python: r >> 3, matrix: r5 << 3 | r5 >> 2
    G: 6 bits (0-63)  — Python: g >> 2, matrix: g6 << 2 | g6 >> 4
    B: 5 bits (0-31)  — Python: b >> 3, matrix: b5 << 3 | b5 >> 2

Maximum quantization error per channel:
    R, B: ±7 counts  (lose bottom 3 bits of 8)
    G:    ±3 counts  (lose bottom 2 bits of 8)

These are imperceptible — none reach the ≥8-count threshold for a noticeable
colour shift.

Endianness: both sides use little-endian uint16 (<u2 in NumPy, array('H') in
CircuitPython on the M4 which is itself little-endian).  There is no byte-swap
artifact.

-------------------------------------------------------------------------------
What causes the artifacts? (and how to tell them apart)
-------------------------------------------------------------------------------

Since RGB565 quantization (max ±7 counts) is ruled out, the visible bright
green/magenta/wrong-colour pixels on the physical panel come from elsewhere:

1. Rolling-shutter / scan artifact  [most likely for camera photos]
   The LED matrix is scanned row-by-row at ~3 kHz.  A phone camera shutter
   captures it mid-scan — some rows are in the middle of being updated, so they
   show the previous frame's colour.  These artifacts MOVE between photos of
   the same static frame.

2. Camera exposure bloom  [likely when matrix is bright]
   The matrix can exceed 100 cd/m² while the ambient scene is much dimmer.
   The camera auto-exposes for the scene; the matrix then overdrives the
   sensor, causing adjacent pixels to bleed colour into each other.

3. Individual LED hardware variation  [permanent, consistent]
   Cheap RGB LED panels have ±20-30% LED-to-LED variation in colour and
   brightness.  A green sub-pixel running hotter than its neighbours reads as
   teal instead of white.  These artifacts are in the SAME position every photo.

4. Serial bit flip  [very rare]
   A single flipped bit in a 16-bit RGB565 word can swing one channel by up to
   248 counts, producing a single-pixel primary-colour spike.  Very rare at
   4 Mbaud USB-CDC but theoretically possible.

How to distinguish them:
    Camera artifact vs. stuck LED:  take multiple photos of the same static
        frame.  Camera artifacts move; stuck LEDs stay put.
    Hardware variation:  display a solid-colour frame (all white, all red).
        Variation is obvious against a flat field.
    Serial bit flip:  compare two photos taken within the same second.
        A bit-flip artifact appears in at most one frame; a stuck LED is always
        there.

To rule out any processing in the save path, use the _raw BMP (the actual
pre-conversion frame written in debug mode) instead of the normal snapshot:

    uv run --project pro python docs/compare_rgb565.py pro/snapshot_*_raw.bmp
"""

import sys
import numpy as np
from PIL import Image
from pathlib import Path


def to_rgb565_and_back(img: np.ndarray) -> np.ndarray:
    """Round-trip RGB888 through RGB565 quantization.

    The matrix receives 16-bit RGB565 over serial.  When it drives the LEDs
    it decodes those 16 bits back to R5, G6, B5 — losing the bottom 3 (R,B)
    or 2 (G) bits of each channel.  This function simulates that loss.

    RGB565 packing:   RRRRRGGG GGGBBBBB
    R: bits 15-11 (5 bits) → expand back by (r5 << 3 | r5 >> 2)
    G: bits 10-5  (6 bits) → expand back by (g6 << 2 | g6 >> 4)
    B: bits  4-0  (5 bits) → expand back by (b5 << 3 | b5 >> 2)
    """
    r = img[:, :, 0].astype(np.uint16)
    g = img[:, :, 1].astype(np.uint16)
    b = img[:, :, 2].astype(np.uint16)

    # Quantize to RGB565 bit-depth
    r5 = (r >> 3) & 0x1F   # keep top 5 bits
    g6 = (g >> 2) & 0x3F   # keep top 6 bits
    b5 = (b >> 3) & 0x1F   # keep top 5 bits

    # Expand back to 8 bits (the matrix reconstructs this way)
    r8 = ((r5 << 3) | (r5 >> 2)).astype(np.uint8)
    g8 = ((g6 << 2) | (g6 >> 4)).astype(np.uint8)
    b8 = ((b5 << 3) | (b5 >> 2)).astype(np.uint8)

    return np.stack([r8, g8, b8], axis=2)


def main() -> None:
    # --- pick a BMP file ---
    if len(sys.argv) > 1:
        bmp_path = Path(sys.argv[1])
    else:
        candidates = sorted(
            Path("pro").glob("snapshot_*.bmp"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        # skip _raw files; those are the pre-processed frame
        candidates = [p for p in candidates if "_raw" not in p.name]
        if not candidates:
            print("No snapshot BMPs found in pro/")
            sys.exit(1)
        bmp_path = candidates[0]

    print(f"Comparing: {bmp_path}")

    original = np.array(Image.open(bmp_path).convert("RGB"))
    roundtripped = to_rgb565_and_back(original)

    # Per-channel and per-pixel difference
    diff = roundtripped.astype(np.int16) - original.astype(np.int16)
    abs_diff = np.abs(diff).astype(np.uint8)
    max_diff_per_pixel = abs_diff.max(axis=2)        # worst channel per pixel

    n_pixels = original.shape[0] * original.shape[1]
    changed = (max_diff_per_pixel > 0).sum()
    bad = (max_diff_per_pixel >= 8).sum()             # visually noticeable shift

    print(f"\nImage size: {original.shape[1]}×{original.shape[0]} = {n_pixels} pixels")
    print(f"Changed pixels (any channel):    {changed:4d} / {n_pixels}  ({100*changed/n_pixels:.1f}%)")
    print(f"Noticeably shifted (≥8 counts):  {bad:4d} / {n_pixels}  ({100*bad/n_pixels:.1f}%)")

    # Worst offenders — pixels where any channel shifts by ≥8
    ys, xs = np.where(max_diff_per_pixel >= 8)
    if len(ys):
        print(f"\nTop 10 worst pixels (row, col)  original→roundtripped  shift:")
        order = np.argsort(-max_diff_per_pixel[ys, xs])[:10]
        for i in order:
            y, x = ys[i], xs[i]
            o = original[y, x]
            r = roundtripped[y, x]
            d = diff[y, x]
            print(
                f"  ({y:2d},{x:2d})  "
                f"RGB({o[0]:3d},{o[1]:3d},{o[2]:3d}) → "
                f"RGB({r[0]:3d},{r[1]:3d},{r[2]:3d})  "
                f"Δ({d[0]:+d},{d[1]:+d},{d[2]:+d})"
            )

    # Channel-level stats
    print("\nPer-channel max shift (original - roundtripped):")
    for i, name in enumerate(("R", "G", "B")):
        c = diff[:, :, i]
        print(f"  {name}: max={c.max():+d}  min={c.min():+d}  mean={c.mean():+.2f}")

    # Save a 10× magnified diff image so you can see where the artifacts are
    scale = 10
    h, w = original.shape[:2]
    out_h, out_w = h * scale, w * scale

    # Amplify diff 4× so small differences are visible
    diff_vis = np.clip(abs_diff * 4, 0, 255).astype(np.uint8)

    orig_large = np.array(Image.fromarray(original).resize((out_w, out_h), Image.NEAREST))
    rt_large = np.array(Image.fromarray(roundtripped).resize((out_w, out_h), Image.NEAREST))
    diff_large = np.array(Image.fromarray(diff_vis).resize((out_w, out_h), Image.NEAREST))

    # Side-by-side: original | roundtripped | diff (4× amplified)
    combined = np.hstack([orig_large, rt_large, diff_large])
    out_path = bmp_path.with_name(bmp_path.stem + "_rgb565_compare.png")
    Image.fromarray(combined).save(out_path)
    print(f"\nSaved comparison image: {out_path}")
    print("  Left:   original BMP (what software saved)")
    print("  Centre: after RGB565 roundtrip (what matrix displays)")
    print("  Right:  |difference| × 4 (artifact map)")


if __name__ == "__main__":
    main()
