# Pixel Font Reference

CircuitPython ships with one built-in font: `terminalio.FONT` (≈6×8 px per character).
On a 64×32 display, four lines of text at 7 px steps share ~1 px between adjacent rows.
This is usually acceptable. If you want pixel-perfect gap-free text, you can draw
characters as bitmaps directly into the game's `_bmp` bitmap — no extra library needed.

---

## Why `terminalio.FONT` overlaps

`label.Label` positions text so `y` is the **vertical centre** of the character cell.
The cell is approximately 8 px tall, so:

| y value | top row | bottom row |
|---------|---------|------------|
| 5       | ~1      | ~9         |
| 12      | ~8      | ~16        |
| 19      | ~15     | ~23        |
| 26      | ~22     | ~30        |

Rows 8–9, 15–16, 22–23 are each shared by two lines → ~1 px bleed.
To eliminate it entirely you need 9 px steps, which means the 4th line clips at y=32.

---

## Hand-drawn 3×5 pixel font

Each glyph is 3 px wide × 5 px tall; rows are 3-bit bitmaps where bit 2 = left pixel.
Characters advance 4 px per glyph (3 px body + 1 px gap).

```python
_DIGITS = [
    [0b111, 0b101, 0b101, 0b101, 0b111],  # 0
    [0b010, 0b110, 0b010, 0b010, 0b111],  # 1
    [0b111, 0b001, 0b111, 0b100, 0b111],  # 2
    [0b111, 0b001, 0b111, 0b001, 0b111],  # 3
    [0b101, 0b101, 0b111, 0b001, 0b001],  # 4
    [0b111, 0b100, 0b111, 0b001, 0b111],  # 5
    [0b111, 0b100, 0b111, 0b101, 0b111],  # 6
    [0b111, 0b001, 0b001, 0b001, 0b001],  # 7
    [0b111, 0b101, 0b111, 0b101, 0b111],  # 8
    [0b111, 0b101, 0b111, 0b001, 0b111],  # 9
]

_CHARS = {
    'A': [0b010, 0b101, 0b111, 0b101, 0b101],
    'B': [0b110, 0b101, 0b110, 0b101, 0b110],
    'C': [0b011, 0b100, 0b100, 0b100, 0b011],
    'E': [0b111, 0b100, 0b110, 0b100, 0b111],
    'N': [0b110, 0b101, 0b101, 0b101, 0b101],
    'O': [0b010, 0b101, 0b101, 0b101, 0b010],
    'R': [0b110, 0b101, 0b110, 0b101, 0b101],
    'S': [0b011, 0b100, 0b010, 0b001, 0b110],
    'T': [0b111, 0b010, 0b010, 0b010, 0b010],
    'U': [0b101, 0b101, 0b101, 0b101, 0b111],
    'W': [0b101, 0b101, 0b101, 0b111, 0b010],
    '-': [0b000, 0b000, 0b111, 0b000, 0b000],
    '!': [0b010, 0b010, 0b010, 0b000, 0b010],
    ' ': [0b000, 0b000, 0b000, 0b000, 0b000],
}
```

### Drawing function

```python
def _draw_chars(text, x, y, c):
    """Draw a string at physical (x, y) using 3×5 pixel bitmaps."""
    cx = x
    for ch in text:
        rows = _DIGITS[int(ch)] if ch.isdigit() else _CHARS.get(ch)
        if rows:
            for r, bits in enumerate(rows):
                for b in range(3):
                    if bits & (1 << (2 - b)):
                        px, py = cx + b, y + r
                        if 0 <= px < _PHYS_W and 0 <= py < _PHYS_H:
                            _bmp[px, py] = c
        cx += 4
```

### Stats screen replacement (gap-free, 4 lines at y=2,9,16,23)

```python
def _show_stats_screen(display, score, stats, button_up, button_down, ext_button):
    _init_mode(False)
    _lbl.hidden = True
    _lbl2.hidden = True
    bitmaptools.fill_region(_bmp, 0, 0, _PHYS_W, _PHYS_H, _BLK)

    new_best = score > 0 and score >= stats["high_score"]
    header = "NEW BEST!" if new_best else "- STATS -"
    header_x = max(0, (_PHYS_W - len(header) * 4 - 1) // 2)
    _draw_chars(header,                           header_x, 2,  _FIRE if new_best else _YEL)
    _draw_chars(f"SCORE {score}",                 4,        9,  _WHT)
    _draw_chars(f"BEST  {stats['high_score']}",   4,        16, _CYN)
    _draw_chars(f"RUNS  {stats['games_played']}",  4,        23, _PIPE)

    display.root_group = _grp
    display.refresh()
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell or ext_button.fell:
            break
        time.sleep(0.02)
```

This writes directly into the game's `_bmp` bitmap (already in `_grp`), so
`display.root_group = _grp` is all that's needed — no new `displayio.Group`.
The `_lbl` / `_lbl2` overlay labels must be hidden first.
