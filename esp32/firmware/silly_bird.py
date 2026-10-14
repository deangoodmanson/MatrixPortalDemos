"""
Waveshare ESP32-C6 LCD 1.47 — Silly Bird (v1 port)
Flappy Bird-style game, ported from matrix-portal/silly_bird.py.

v1 scope, decided for this board's hardware:
  - Landscape only — no mode picker, no portrait mode (board.DISPLAY defaults
    to a 172x320 panel; set to rotation=90 for 320x172 landscape before calling
    run()). Revisit if portrait is wanted later.
  - Single button (board.BUTTON, i.e. board.IO9) does everything: flap during
    play, dismiss/restart on the OOF! and stats screens. This board exposes
    only one user-readable button to CircuitPython (the schematic's second
    key is not broken out as a board.* pin in this firmware build) — unlike
    the Matrix Portal's three inputs (UP, DOWN, external flap button).

Rendering: the game still draws onto the same 64x32 logical bitmap as the
Matrix Portal version (same drawing code, same feel), upscaled 2x and
centered inside a 140x140 "safe zone" in the middle of the 320x172 panel —
see SAFE_SQUARE/SAFE_X/SAFE_Y/CONTENT_X/CONTENT_Y below. This keeps the
game well clear of a confirmed hardware defect (corrupted pixels) near one
edge of this particular panel; see esp32/docs/waveshare-esp32-c6-circuitpython-setup.md.

Public API: run(display, button)
Loops game -> stats forever; there is no RESET-equivalent exit on this board,
so the loop just keeps going (reset by unplugging/resetting the board).
Stats are kept in RAM only; nothing is written to the file system.
"""

# ── IMPORTS ───────────────────────────────────────────────────────────────────
import time
import random
import displayio
import bitmaptools
from adafruit_display_text import label
import terminalio


# ── GAME FEEL ─────────────────────────────────────────────────────────────────
# Same numbers as the Matrix Portal version — change these to customize feel.

GRAVITY       = 0.18   # how fast the bird falls    (bigger = falls faster)
FLAP_POWER    = -1.1   # how high one flap goes     (more negative = stronger flap)
DOUBLE_FLAP   = -1.7   # extra boost when the tail fires (chain-flap)
PIPE_GAP      = 9      # pixels between top/bottom pipe   (bigger = easier)
PIPE_WIDTH    = 5      # how wide each pipe is
START_SPEED   = 1.0    # pipe scroll speed at game start
SPEED_UP      = 0.08   # extra speed gained per pipe cleared

BIRD_WIDTH    = 4      # bird hitbox width in pixels
BIRD_HEIGHT   = 3      # bird hitbox height in pixels
BIRD_X        = 10     # bird's fixed horizontal position
GROUND_Y      = 27     # y-coordinate of the ground

VIRTUAL_WIDTH  = 64    # logical game plane — same grid as the Matrix Portal
VIRTUAL_HEIGHT = 32

# The physical panel has a confirmed hardware defect (a vertical band of
# corrupted pixels) near one edge — see esp32/docs/waveshare-esp32-c6-circuitpython-setup.md.
# It's independent of display.rotation, so instead of using the full
# 320x172 landscape panel, the game renders into a square "safe zone"
# inset well clear of every edge.
PANEL_WIDTH    = 320
PANEL_HEIGHT   = 172
SAFE_SQUARE    = 140   # safe-zone side length, centered in the panel
SAFE_X         = (PANEL_WIDTH  - SAFE_SQUARE) // 2   # = 90
SAFE_Y         = (PANEL_HEIGHT - SAFE_SQUARE) // 2   # = 16

SCALE          = 2     # 64*2=128, 32*2=64 — both fit inside the 140x140 safe zone
CONTENT_X      = SAFE_X + (SAFE_SQUARE - VIRTUAL_WIDTH  * SCALE) // 2  # = 96
CONTENT_Y      = SAFE_Y + (SAFE_SQUARE - VIRTUAL_HEIGHT * SCALE) // 2  # = 54

FRAME_DELAY   = 0.05   # seconds between frames     (smaller = faster game)


# ── COLORS ────────────────────────────────────────────────────────────────────

COLOR_SKY    = 0x001040   # dark blue sky
COLOR_GROUND = 0x7A5C1E   # brown ground
COLOR_PIPE   = 0x00AA00   # green pipe body
COLOR_CAP    = 0x007700   # darker green pipe cap
COLOR_BIRD   = 0xFFD700   # yellow bird
COLOR_WHITE  = 0xFFFFFF   # bird eye white
COLOR_BLACK  = 0x000000   # bird pupil / background fill
COLOR_SCORE  = 0x00FFCC   # cyan score digits
COLOR_SMOKE  = 0x888888   # grey smoke puff
COLOR_FIRE   = 0xFF6600   # orange fire puff (every 3rd chain-flap)


# ── PALETTE / DISPLAY SETUP ───────────────────────────────────────────────────

SKY, GND, PIPE, CAP, YEL, WHT, BLK, CYN, GREY, FIRE = range(10)

palette = displayio.Palette(10)
palette[SKY]  = COLOR_SKY
palette[GND]  = COLOR_GROUND
palette[PIPE] = COLOR_PIPE
palette[CAP]  = COLOR_CAP
palette[YEL]  = COLOR_BIRD
palette[WHT]  = COLOR_WHITE
palette[BLK]  = COLOR_BLACK
palette[CYN]  = COLOR_SCORE
palette[GREY] = COLOR_SMOKE
palette[FIRE] = COLOR_FIRE

# One 64x32 logical bitmap, upscaled 5x and letterboxed onto the 320x172 panel.
# displayio.TileGrid has no `scale` attribute of its own — scaling lives on
# Group, so the tile grid sits in its own scaled sub-group, and the letterbox
# offset is applied to that sub-group's (unscaled) y position.
bmp = displayio.Bitmap(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, 16)
tile_grid = displayio.TileGrid(bmp, pixel_shader=palette)
scaled_group = displayio.Group(scale=SCALE)
scaled_group.append(tile_grid)
scaled_group.x = CONTENT_X
scaled_group.y = CONTENT_Y
grp = displayio.Group()
grp.append(scaled_group)

# Overlay labels (OOF!, stats text) are drawn in full-panel coordinates
# (320x172), not the 64x32 logical plane, so they stay crisp instead of
# being blown up 5x along with the game bitmap.
lbl  = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF)
lbl.hidden = True
grp.append(lbl)
lbl2 = label.Label(terminalio.FONT, text=" ", color=0xAAAAAA)
lbl2.hidden = True
grp.append(lbl2)


# ── SCORE DIGITS ──────────────────────────────────────────────────────────────
# Each digit is a 3-wide x 5-tall picture made of characters:
#   '#' = light this pixel,   ' ' = leave it dark.

DIGITS = [
    ["###",
     "# #",
     "# #",
     "# #",
     "###"],  # 0
    [" # ",
     "## ",
     " # ",
     " # ",
     "###"],  # 1
    ["###",
     "  #",
     "###",
     "#  ",
     "###"],  # 2
    ["###",
     "  #",
     "###",
     "  #",
     "###"],  # 3
    ["# #",
     "# #",
     "###",
     "  #",
     "  #"],  # 4
    ["###",
     "#  ",
     "###",
     "  #",
     "###"],  # 5
    ["###",
     "#  ",
     "###",
     "# #",
     "###"],  # 6
    ["###",
     "  #",
     "  #",
     "  #",
     "  #"],  # 7
    ["###",
     "# #",
     "###",
     "# #",
     "###"],  # 8
    ["###",
     "# #",
     "###",
     "  #",
     "###"],  # 9
]


# ── GAME OBJECTS ──────────────────────────────────────────────────────────────

class Pipe:
    """One scrolling pipe pair (top + bottom with a gap in the middle)."""
    def __init__(self, x, gap_y):
        self.x      = x          # x-coordinate of the pipe's left edge
        self.gap_y  = gap_y      # y-coordinate of the top of the gap
        self.scored = False      # True once the bird has flown past this pipe


class Puff:
    """A trailing smoke or fire puff behind the bird."""
    def __init__(self, x, y, is_fire):
        self.x       = x
        self.y       = y
        self.age     = 0         # frames since the puff was spawned
        self.is_fire = is_fire   # fire puff every 3rd chain-flap, smoke otherwise


# ── DRAWING HELPERS ───────────────────────────────────────────────────────────
# All drawing uses the 64x32 logical plane — identical to the Matrix Portal
# version. TileGrid.scale handles the upscale to the physical panel.

def box(vx, vy, vw, vh, color_index):
    """Fill a rectangle in the logical bitmap, clipped to its bounds."""
    x1 = max(0, vx); x2 = min(VIRTUAL_WIDTH,  vx + vw)
    y1 = max(0, vy); y2 = min(VIRTUAL_HEIGHT, vy + vh)
    if x2 > x1 and y2 > y1:
        bitmaptools.fill_region(bmp, x1, y1, x2, y2, color_index)


def dot(vx, vy, color_index):
    """Set a single pixel in the logical bitmap, clipped to its bounds."""
    if 0 <= vx < VIRTUAL_WIDTH and 0 <= vy < VIRTUAL_HEIGHT:
        bmp[vx, vy] = color_index


def draw_score(n):
    """Draw the current score in the top-left corner."""
    x = 1
    for ch in str(n):
        for row_idx, row in enumerate(DIGITS[int(ch)]):
            for col_idx, glyph in enumerate(row):
                if glyph == '#':
                    dot(x + col_idx, 1 + row_idx, CYN)
        x += 4


def draw_bird(by, bird_v=0.0):
    """Draw the bird at vertical position by, with a tiny wing flick when moving."""
    by = int(by)
    bx = BIRD_X
    box(bx + 1, by,     2, 1, YEL)
    dot(bx,     by + 1, YEL)
    dot(bx + 1, by + 1, WHT)
    dot(bx + 2, by + 1, BLK)
    dot(bx + 3, by + 1, FIRE)
    box(bx,     by + 2, 3, 1, YEL)
    # A 1-pixel wing tip flips above or below depending on climbing vs diving
    if bird_v < -0.5:
        dot(bx + 1, by - 1, YEL)
    elif bird_v > 0.5 and by + BIRD_HEIGHT < GROUND_Y:
        dot(bx + 1, by + BIRD_HEIGHT, YEL)


def draw_puff(puff):
    """Draw a smoke or fire puff trailing behind the bird."""
    color = FIRE if puff.is_fire else GREY
    # Young puffs are a small cluster; old puffs shrink to a single trailing dot
    if puff.age == 0:
        dot(puff.x,     puff.y,     color)
        dot(puff.x - 1, puff.y - 1, color)
        dot(puff.x - 1, puff.y + 1, color)
    else:
        dot(puff.x - 2, puff.y, color)


def draw_pipe(pipe):
    """Draw a green pipe with a gap centred at pipe.gap_y."""
    px = int(pipe.x)
    gy = pipe.gap_y
    pw = PIPE_WIDTH
    # Top pipe: body then darker cap
    if gy > 2:
        box(px, 0, pw, gy - 2, PIPE)
    if gy > 0:
        box(px - 1, gy - 2, pw + 2, 2, CAP)
    # Bottom pipe: cap then body, stopping above the ground
    bot = gy + PIPE_GAP
    if bot < GROUND_Y:
        box(px - 1, bot, pw + 2, 2, CAP)
    if bot + 2 < GROUND_Y:
        box(px, bot + 2, pw, GROUND_Y - bot - 2, PIPE)


def draw_scene():
    """Paint the sky and ground — the background for every frame."""
    box(0, 0,        VIRTUAL_WIDTH, GROUND_Y,                  SKY)
    box(0, GROUND_Y, VIRTUAL_WIDTH, VIRTUAL_HEIGHT - GROUND_Y, GND)


def poll_flap(button, duration):
    """Poll the button every 5ms for `duration` seconds; return True if it
    was pressed at any point during that window.

    A single button.update() per frame (every FRAME_DELAY=0.05s) missed
    quick taps entirely — a tap shorter than one frame can start and finish
    between two polls, so it never registers as a fell edge. Confirmed on
    hardware: holding the button worked, a quick tap did not. Sampling every
    5ms across the whole frame window instead of once per frame catches it.
    """
    flapped = False
    end = time.monotonic() + duration
    while time.monotonic() < end:
        button.update()
        if button.fell:
            flapped = True
        time.sleep(0.005)
    return flapped


# ── COLLISION DETECTION ───────────────────────────────────────────────────────

def collides(by, pipes):
    """Return True if the bird's box overlaps any pipe."""
    by = int(by)
    for pipe in pipes:
        px = int(pipe.x)
        gy = pipe.gap_y
        # Check horizontal overlap first, then vertical (above-gap or below-gap)
        if BIRD_X + BIRD_WIDTH > px and BIRD_X < px + PIPE_WIDTH:
            if by < gy or by + BIRD_HEIGHT > gy + PIPE_GAP:
                return True
    return False


# ── SCREEN FUNCTIONS ──────────────────────────────────────────────────────────

def show_stats_screen(display, score, stats, button):
    """Show the post-game stats screen until the button is pressed.

    Label positions are in full-panel (320x172) coordinates, not the 64x32
    logical plane.
    """
    # Positioned inside the SAFE_SQUARE zone (see module header), not full-panel
    # coordinates — keeps text clear of the damaged edge of the panel.
    new_best = score > 0 and score >= stats["high_score"]
    g = displayio.Group()
    g.append(label.Label(terminalio.FONT,
        text="NEW BEST!" if new_best else "- STATS -",
        color=0xFF6600 if new_best else 0xFFD700, x=SAFE_X + 5, y=SAFE_Y + 20, scale=2))
    g.append(label.Label(terminalio.FONT,
        text=f"SCORE {score}", color=0xFFFFFF, x=SAFE_X + 5, y=SAFE_Y + 55, scale=2))
    g.append(label.Label(terminalio.FONT,
        text=f"BEST  {stats['high_score']}", color=0x00FFCC, x=SAFE_X + 5, y=SAFE_Y + 90, scale=2))
    g.append(label.Label(terminalio.FONT,
        text=f"RUNS  {stats['games_played']}", color=0x00FF00, x=SAFE_X + 5, y=SAFE_Y + 120, scale=2))
    display.root_group = g
    display.refresh()
    # Wait for the OOF!-dismiss press to be released before listening for a fresh one
    while not button.value:
        button.update()
        time.sleep(0.01)
    while True:
        button.update()
        if button.fell:
            break
        time.sleep(0.02)
    display.root_group = grp


# ── MAIN GAME LOOP ────────────────────────────────────────────────────────────

def run(display, button):
    """Run Silly Bird from game to game forever (landscape only, single button).

    The game runs in two nested loops:
      outer loop  — one full game (bird moves, pipes scroll, score counts)
      inner reads — button checked every frame (~20 FPS)

    There is no mode picker and no orientation choice in this v1 — the caller
    is expected to have already set display.rotation for landscape (320x172)
    before calling run(). There is also no hardware-level exit; crashing just
    starts another round.
    """
    print("Launching Silly Bird (ESP32-C6 v1)...")
    display.root_group = grp

    # Wait for any button hold from startup to be released
    while not button.value:
        button.update()
        time.sleep(0.01)

    # Session stats — kept in RAM only, never written to disk
    stats = {"high_score": 0, "games_played": 0}

    while True:  # outer loop: game -> stats -> next game
        lbl.hidden  = True
        lbl2.hidden = True

        # ── Game loop ─────────────────────────────────────────────────────────
        # Pre-spawn one "intro" pipe positioned around the bird so the round
        # doesn't force an instant crash — see matrix-portal/silly_bird.py for
        # the original rationale (unchanged here).
        bird_y       = float(GROUND_Y // 2)
        bird_v       = 0.0
        centered_gap = int(bird_y) - (PIPE_GAP - BIRD_HEIGHT) // 2
        gap_min      = 4
        gap_max      = GROUND_Y - PIPE_GAP - 4
        intro_gap_y  = max(gap_min, min(gap_max, centered_gap))
        pipes        = [Pipe(float(BIRD_X), intro_gap_y)]
        score        = 0
        spd          = START_SPEED
        dist         = float(VIRTUAL_WIDTH)
        puffs        = []
        climb_flap_count = 0
        flapped      = False  # carried over from the previous frame's poll_flap window

        while True:
            # Any button press is a flap; consecutive climbing flaps spawn puffs
            if flapped:
                if bird_v < 0:
                    climb_flap_count += 1
                    if climb_flap_count > 1:
                        is_fire = (climb_flap_count % 3 == 0)
                        puffs.append(Puff(BIRD_X - 2, int(bird_y) + 1, is_fire))
                        bird_v = DOUBLE_FLAP   # double-jump boost when the tail fires
                    else:
                        bird_v = FLAP_POWER
                else:
                    climb_flap_count = 0
                    bird_v = FLAP_POWER

            # Physics: gravity pulls the bird down each frame
            bird_v += GRAVITY
            bird_y += bird_v

            # Stop the bird from going through the ceiling or the ground
            if bird_y < 0:
                bird_y = 0.0
                bird_v = 0.0
            if bird_y + BIRD_HEIGHT >= GROUND_Y:
                bird_y = float(GROUND_Y - BIRD_HEIGHT)
                bird_v = 0.0

            # Pipes only scroll when the bird is alive (in the air)
            if bird_y + BIRD_HEIGHT < GROUND_Y:
                dist -= spd
                if dist <= 0:
                    dist = float(VIRTUAL_WIDTH)
                    gy = random.randint(4, GROUND_Y - PIPE_GAP - 4)
                    pipes.append(Pipe(float(VIRTUAL_WIDTH), gy))
                kept = []
                for pipe in pipes:
                    pipe.x -= spd
                    # Score when the bird's left edge passes the pipe's right edge
                    if not pipe.scored and pipe.x + PIPE_WIDTH < BIRD_X:
                        pipe.scored = True
                        score += 1
                        spd = START_SPEED + score * SPEED_UP
                    if pipe.x > -PIPE_WIDTH - 2:
                        kept.append(pipe)
                pipes = kept

            # Redraw the world this frame
            draw_scene()
            for pipe in pipes:
                draw_pipe(pipe)
            # Age each puff; drop ones older than 1 frame
            alive = []
            for puff in puffs:
                draw_puff(puff)
                puff.age += 1
                if puff.age < 2:
                    alive.append(puff)
            puffs = alive
            draw_bird(bird_y, bird_v)
            draw_score(score)
            display.refresh()

            if collides(bird_y, pipes):
                break

            flapped = poll_flap(button, FRAME_DELAY)   # ~20 FPS at 0.05s, polled every 5ms

        # ── Game over ─────────────────────────────────────────────────────────
        # "OOF!" overlaid on the crash frame, in full-panel coordinates.
        lbl.text   = "OOF!"
        lbl.color  = 0xFF2200
        lbl.scale  = 3
        lbl.x, lbl.y = 110, 60   # roughly centered on the 320x172 panel
        lbl.hidden = False
        lbl2.hidden = True
        display.refresh()

        # Update stats and announce the result over USB serial
        stats["games_played"] += 1
        if score > stats["high_score"]:
            stats["high_score"] = score
        print(f"Silly Bird — score: {score}  best: {stats['high_score']}  runs: {stats['games_played']}")

        # Wait for the crash-causing flap to be released, then for a fresh
        # press to dismiss OOF! — otherwise tap-spam would skip the OOF! screen.
        while not button.value:
            button.update()
            time.sleep(0.01)
        while True:
            button.update()
            if button.fell:
                break
            time.sleep(0.02)

        show_stats_screen(display, score, stats, button)
        # loop back to a new round
