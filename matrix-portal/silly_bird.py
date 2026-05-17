"""
Matrix Portal M4 — Silly Bird
Flappy Bird-style game for the 64×32 LED matrix.
Public API: run(display, button_up, button_down, ext_button)
Loops title→game→stats until DOWN is pressed on the title screen.
Stats are kept in RAM for the session.
"""
import time
import random
import displayio
import bitmaptools
from adafruit_display_text import label
import terminalio

W, H = 64, 32

# Palette indices
_SKY, _GND, _PIPE, _CAP, _YEL, _WHT, _BLK, _CYN = range(8)
_GREY = 8   # smoke puff
_FIRE = 9   # fire puff (every 3rd consecutive climbing flap)

_pal = displayio.Palette(10)
_pal[_SKY]  = 0x001040
_pal[_GND]  = 0x7A5C1E
_pal[_PIPE] = 0x00AA00
_pal[_CAP]  = 0x007700
_pal[_YEL]  = 0xFFD700
_pal[_WHT]  = 0xFFFFFF
_pal[_BLK]  = 0x000000
_pal[_CYN]  = 0x00FFCC
_pal[_GREY] = 0x888888
_pal[_FIRE] = 0xFF6600

_bmp = displayio.Bitmap(W, H, 16)
_tg  = displayio.TileGrid(_bmp, pixel_shader=_pal)
_grp = displayio.Group()
_grp.append(_tg)
_lbl = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF)
_grp.append(_lbl)

# Game constants
_GY   = 27      # ground top y
_BX   = 10      # bird fixed x
_BW   = 4       # bird width
_BH   = 3       # bird height
_PW   = 5       # pipe width
_GAP  = 9       # gap between top/bottom pipe
_GRAV = 0.18
_FLAP = -1.1
_SPD0 = 1.0

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


def _show_stats_screen(display, score, stats, button_up, button_down, ext_button):
    new_best = score > 0 and score >= stats["high_score"]
    grp = displayio.Group()
    grp.append(label.Label(terminalio.FONT,
        text="NEW BEST!" if new_best else "- STATS -",
        color=0xFF6600 if new_best else 0xFFD700, x=4, y=3))
    grp.append(label.Label(terminalio.FONT,
        text=f"SCORE {score}", color=0xFFFFFF, x=4, y=12))
    grp.append(label.Label(terminalio.FONT,
        text=f"BEST  {stats['high_score']}", color=0x00FFCC, x=4, y=21))
    grp.append(label.Label(terminalio.FONT,
        text=f"RUNS  {stats['games_played']}", color=0x00FF00, x=4, y=28))
    display.root_group = grp
    display.refresh()
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell or ext_button.fell:
            break
        time.sleep(0.02)


def _box(x, y, w, h, c):
    x1 = max(0, x);   y1 = max(0, y)
    x2 = min(W, x+w); y2 = min(H, y+h)
    if x2 > x1 and y2 > y1:
        bitmaptools.fill_region(_bmp, x1, y1, x2, y2, c)

def _dot(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        _bmp[x, y] = c

def _draw_score(n):
    x = 1
    for ch in str(n):
        rows = _DIGITS[int(ch)]
        for r, bits in enumerate(rows):
            for b in range(3):
                if bits & (1 << (2 - b)):
                    _dot(x + b, 1 + r, _CYN)
        x += 4

def _draw_bird(by, bird_v=0.0):
    by = int(by)
    _box(_BX + 1, by,     2, 1, _YEL)
    _dot(_BX,     by + 1, _YEL)
    _dot(_BX + 1, by + 1, _WHT)
    _dot(_BX + 2, by + 1, _BLK)
    _dot(_BX + 3, by + 1, _FIRE)
    _box(_BX,     by + 2, 3, 1, _YEL)
    if bird_v < -0.5:
        _dot(_BX + 1, by - 1, _YEL)
    elif bird_v > 0.5 and by + _BH < _GY:
        _dot(_BX + 1, by + _BH, _YEL)

def _draw_puff(puff):
    x, y, age, is_fire = puff[0], puff[1], puff[2], puff[3]
    c = _FIRE if is_fire else _GREY
    if age == 0:
        _dot(x,     y,     c)
        _dot(x - 1, y - 1, c)
        _dot(x - 1, y + 1, c)
    else:
        _dot(x - 2, y, c)

def _draw_pipe(px, gy):
    px = int(px)
    if gy > 2:
        _box(px, 0, _PW, gy - 2, _PIPE)
    if gy > 0:
        _box(px - 1, gy - 2, _PW + 2, 2, _CAP)
    bot = gy + _GAP
    if bot < _GY:
        _box(px - 1, bot, _PW + 2, 2, _CAP)
    if bot + 2 < _GY:
        _box(px, bot + 2, _PW, _GY - bot - 2, _PIPE)

def _draw_scene():
    _box(0, 0, W, _GY, _SKY)
    _box(0, _GY, W, H - _GY, _GND)

def _collides(by, pipes):
    by = int(by)
    for p in pipes:
        px = int(p[0])
        gy = p[1]
        if _BX + _BW > px and _BX < px + _PW:
            if by < gy or by + _BH > gy + _GAP:
                return True
    return False


def run(display, button_up, button_down, ext_button):
    """Run Silly Bird. Loops title→game→stats until DOWN is pressed on the title screen."""
    print("Launching Silly Bird...")

    # Session stats kept in RAM
    stats = {"high_score": 0, "games_played": 0}

    # Drain buttons still held from the DOWN press that launched us
    while not button_up.value or not button_down.value or not ext_button.value:
        button_up.update(); button_down.update(); ext_button.update()
        time.sleep(0.01)

    while True:  # outer loop: title → game → stats → title
        # ── Title screen ──────────────────────────────────────────────────────
        display.root_group = _grp
        _draw_scene()
        _draw_pipe(44, 8)
        _draw_pipe(30, 14)
        _draw_bird(_GY // 2 - 1)
        _lbl.text = "FLAP!"
        _lbl.color = 0xFFD700
        _lbl.x, _lbl.y = 17, 8
        _lbl.hidden = False
        display.refresh()

        # DOWN = exit back to camera feed; UP/EXT = play
        while True:
            button_up.update(); button_down.update(); ext_button.update()
            if button_down.fell:
                return
            if button_up.fell or ext_button.fell:
                break
            time.sleep(0.02)

        # ── Game loop ─────────────────────────────────────────────────────────
        _lbl.hidden     = True
        bird_y          = float(_GY // 2)
        bird_v          = 0.0
        pipes           = []
        score           = 0
        spd             = _SPD0
        dist            = 32.0
        puffs           = []
        climb_flap_count = 0

        while True:
            button_up.update(); button_down.update(); ext_button.update()
            if not button_up.value and not button_down.value:
                return                              # both buttons held = quit
            if button_up.fell or button_down.fell or ext_button.fell:
                if bird_v < 0:
                    climb_flap_count += 1
                    if climb_flap_count > 1:
                        is_fire = (climb_flap_count % 3 == 0)
                        puffs.append([_BX - 2, int(bird_y) + 1, 0, is_fire])
                else:
                    climb_flap_count = 0
                bird_v = _FLAP

            bird_v += _GRAV
            bird_y += bird_v

            if bird_y < 0:
                bird_y = 0.0
                bird_v = 0.0
            if bird_y + _BH >= _GY:
                bird_y = float(_GY - _BH)
                bird_v = 0.0

            if bird_y + _BH < _GY:
                dist -= spd
                if dist <= 0:
                    dist = 32.0
                    gy = random.randint(4, _GY - _GAP - 4)
                    pipes.append([float(W), gy, False])
                kept = []
                for p in pipes:
                    p[0] -= spd
                    if not p[2] and p[0] + _PW < _BX:
                        p[2] = True
                        score += 1
                        spd = _SPD0 + score * 0.08
                    if p[0] > -_PW - 2:
                        kept.append(p)
                pipes = kept

            _draw_scene()
            for p in pipes:
                _draw_pipe(p[0], p[1])
            alive = []
            for p in puffs:
                _draw_puff(p)
                p[2] += 1
                if p[2] < 2:
                    alive.append(p)
            puffs = alive
            _draw_bird(bird_y, bird_v)
            _draw_score(score)
            display.refresh()

            if _collides(bird_y, pipes):
                break

            time.sleep(0.05)   # ~20 FPS

        # ── Game over ─────────────────────────────────────────────────────────
        _lbl.text = "OOF!"
        _lbl.color = 0xFF2200
        _lbl.x, _lbl.y = 20, 16
        _lbl.hidden = False
        _draw_scene()
        _draw_score(score)
        display.refresh()
        time.sleep(1.5)

        stats["games_played"] += 1
        if score > stats["high_score"]:
            stats["high_score"] = score
        print(f"Silly Bird — score: {score}  best: {stats['high_score']}  runs: {stats['games_played']}")

        _lbl.text = "TAP!"
        _lbl.color = 0xFFFF00
        _lbl.x = 20
        display.refresh()
        while True:
            button_up.update(); button_down.update(); ext_button.update()
            if button_up.fell or button_down.fell or ext_button.fell:
                break
            time.sleep(0.02)

        _show_stats_screen(display, score, stats, button_up, button_down, ext_button)
        # loop back to title
