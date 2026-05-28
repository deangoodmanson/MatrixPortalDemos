"""
Matrix Portal M4 — Silly Bird
Flappy Bird-style game for the 64×32 LED matrix.
Public API: run(display, button_up, button_down, ext_button)
Loops MODE? picker → game → stats forever; RESET is the only exit.
Stats are kept in RAM only; nothing is written to the file system.

Portrait mode uses display.rotation = 90 so labels (which CircuitPython can
only render horizontally) appear upright when the device is held tall with
USB at the bottom.  Each orientation has its own bitmap + group + labels so
the active orientation just sets display.rotation and switches root_group;
the rest of the drawing code uses natural coordinates with no manual rotation.
"""

# ── IMPORTS ───────────────────────────────────────────────────────────────────
import time
import random
import displayio
import bitmaptools
from adafruit_display_text import label
import terminalio


# ── GAME FEEL ─────────────────────────────────────────────────────────────────
# Change these numbers to customize how the game plays!

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
GROUND_Y      = 27     # y-coordinate of the ground in landscape mode

FRAME_DELAY   = 0.05   # seconds between frames     (smaller = faster game)

# Portrait orientation overrides (hold device tall-side up, USB at bottom).
# Portrait has a taller play area, so the gap and pipe width differ — but
# the bird's flap arc is the same number of pixels in both modes.  The bird
# also sits closer to the left edge in portrait: only 32 pixels wide, so
# pushing the bird in from x=10 left only 20 pixels of runway; x=3 gives ~28.
PORTRAIT_BIRD_X     = 3
PORTRAIT_PIPE_GAP   = 14
PORTRAIT_PIPE_WIDTH = 3
PORTRAIT_GROUND_Y   = 56   # ground sits ~87% down the 64-tall play space


# ── COLORS ────────────────────────────────────────────────────────────────────
# Each color is a 24-bit hex value: 0xRRGGBB.
# Find color hex codes at: htmlcolorcodes.com

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
# A palette is a small lookup table: each pixel stores an index (0–9), and
# the palette converts that index into a real RGB color when the matrix draws.

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

# Two bitmap + group pairs — one per orientation. Switching display.rotation
# between 0 (landscape) and 90 (portrait) rotates the bitmap AND any labels
# together, so we don't need any manual coordinate transform anymore.
#
# Each group carries its own label objects positioned in that group's natural
# coordinate space:
#   grp_landscape labels are placed in a 64×32 plane
#   grp_portrait  labels are placed in a 32×64 plane
# Both orientations stay allocated so we can swap quickly between rounds.

bmp_landscape = displayio.Bitmap(64, 32, 16)
grp_landscape = displayio.Group()
grp_landscape.append(displayio.TileGrid(bmp_landscape, pixel_shader=palette))
lbl_landscape  = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF)
lbl_landscape.hidden = True
grp_landscape.append(lbl_landscape)
lbl2_landscape = label.Label(terminalio.FONT, text=" ", color=0xAAAAAA)
lbl2_landscape.hidden = True
grp_landscape.append(lbl2_landscape)

bmp_portrait = displayio.Bitmap(32, 64, 16)
grp_portrait = displayio.Group()
grp_portrait.append(displayio.TileGrid(bmp_portrait, pixel_shader=palette))
lbl_portrait  = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF)
lbl_portrait.hidden = True
grp_portrait.append(lbl_portrait)
lbl2_portrait = label.Label(terminalio.FONT, text=" ", color=0xAAAAAA)
lbl2_portrait.hidden = True
grp_portrait.append(lbl2_portrait)

# Active references — point at the current orientation's bitmap/group/labels.
# start_round() reassigns these before each round.
bmp  = bmp_landscape
grp  = grp_landscape
lbl  = lbl_landscape
lbl2 = lbl2_landscape


# ── SCORE DIGITS ──────────────────────────────────────────────────────────────
# Each digit is a 3-wide × 5-tall picture made of characters:
#   '#' = light this pixel,   ' ' = leave it dark.
# Editing a digit is as easy as editing the picture below — no bit math needed.

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
# Instead of storing pipes and puffs as lists with magic indices (p[0], p[1]…),
# we use tiny classes with named attributes.  pipe.x reads much better than p[0].

class GameMode:
    """Settings for one round — different in landscape vs portrait.

    Bundles every "which numbers change between orientations?" value into a
    single object so the rest of the code reads mode.virtual_width instead of
    having to remember which global to look at.
    """
    def __init__(self, portrait):
        self.portrait    = portrait
        self.bird_width  = BIRD_WIDTH
        self.bird_height = BIRD_HEIGHT
        self.gravity     = GRAVITY
        self.flap_power  = FLAP_POWER
        self.start_speed = START_SPEED
        if portrait:
            # Game plane is 32 wide × 64 tall — taller play area
            self.virtual_width  = 32
            self.virtual_height = 64
            self.bird_x         = PORTRAIT_BIRD_X
            self.ground_y       = PORTRAIT_GROUND_Y
            self.pipe_width     = PORTRAIT_PIPE_WIDTH
            self.pipe_gap       = PORTRAIT_PIPE_GAP
        else:
            # Landscape: 64 wide × 32 tall
            self.virtual_width  = 64
            self.virtual_height = 32
            self.bird_x         = BIRD_X
            self.ground_y       = GROUND_Y
            self.pipe_width     = PIPE_WIDTH
            self.pipe_gap       = PIPE_GAP


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


# Current game mode — replaced by start_round() before each round.
mode = GameMode(portrait=False)


def start_round(display, portrait):
    """Configure orientation for the next round.

    Sets display.rotation and swaps the active bitmap/group/label references
    so the rest of the code can just draw without worrying about orientation.
    """
    global mode, bmp, grp, lbl, lbl2
    mode = GameMode(portrait)
    if portrait:
        bmp, grp = bmp_portrait, grp_portrait
        lbl, lbl2 = lbl_portrait, lbl2_portrait
        display.rotation = 90
    else:
        bmp, grp = bmp_landscape, grp_landscape
        lbl, lbl2 = lbl_landscape, lbl2_landscape
        display.rotation = 0
    display.root_group = grp


# ── DRAWING HELPERS ───────────────────────────────────────────────────────────
# With display.rotation handling the orientation, we draw to whichever bitmap
# matches the current mode using natural coordinates: (0, 0) is always the
# top-left of the player's view, regardless of how they're holding the device.

def box(vx, vy, vw, vh, color_index):
    """Fill a rectangle in the current bitmap, clipped to its bounds."""
    x1 = max(0, vx); x2 = min(mode.virtual_width,  vx + vw)
    y1 = max(0, vy); y2 = min(mode.virtual_height, vy + vh)
    if x2 > x1 and y2 > y1:
        bitmaptools.fill_region(bmp, x1, y1, x2, y2, color_index)


def dot(vx, vy, color_index):
    """Set a single pixel in the current bitmap, clipped to its bounds."""
    if 0 <= vx < mode.virtual_width and 0 <= vy < mode.virtual_height:
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
    bx = mode.bird_x
    box(bx + 1, by,     2, 1, YEL)
    dot(bx,     by + 1, YEL)
    dot(bx + 1, by + 1, WHT)
    dot(bx + 2, by + 1, BLK)
    dot(bx + 3, by + 1, FIRE)
    box(bx,     by + 2, 3, 1, YEL)
    # A 1-pixel wing tip flips above or below depending on climbing vs diving
    if bird_v < -0.5:
        dot(bx + 1, by - 1, YEL)
    elif bird_v > 0.5 and by + mode.bird_height < mode.ground_y:
        dot(bx + 1, by + mode.bird_height, YEL)


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
    pw = mode.pipe_width
    # Top pipe: body then darker cap
    if gy > 2:
        box(px, 0, pw, gy - 2, PIPE)
    if gy > 0:
        box(px - 1, gy - 2, pw + 2, 2, CAP)
    # Bottom pipe: cap then body, stopping above the ground
    bot = gy + mode.pipe_gap
    if bot < mode.ground_y:
        box(px - 1, bot, pw + 2, 2, CAP)
    if bot + 2 < mode.ground_y:
        box(px, bot + 2, pw, mode.ground_y - bot - 2, PIPE)


def draw_scene():
    """Paint the sky and ground — the background for every frame."""
    box(0, 0,             mode.virtual_width, mode.ground_y,                         SKY)
    box(0, mode.ground_y, mode.virtual_width, mode.virtual_height - mode.ground_y,   GND)


# ── COLLISION DETECTION ───────────────────────────────────────────────────────

def collides(by, pipes):
    """Return True if the bird's box overlaps any pipe."""
    by = int(by)
    bx = mode.bird_x
    bw = mode.bird_width
    bh = mode.bird_height
    pw = mode.pipe_width
    gap = mode.pipe_gap
    for pipe in pipes:
        px = int(pipe.x)
        gy = pipe.gap_y
        # Check horizontal overlap first, then vertical (above-gap or below-gap)
        if bx + bw > px and bx < px + pw:
            if by < gy or by + bh > gy + gap:
                return True
    return False


# ── SCREEN FUNCTIONS ──────────────────────────────────────────────────────────

def show_mode_picker(display, button_up, button_down, ext_button):
    """Show the orientation picker; return True for portrait, False for landscape.

    UP or EXT → landscape (False, the default)
    DOWN      → portrait  (True)
    """
    display.rotation = 0     # always show the picker upright in landscape
    g = displayio.Group()
    g.append(label.Label(terminalio.FONT, text="MODE?",      color=0xFFD700, x=17, y=5))
    g.append(label.Label(terminalio.FONT, text="WIDE: UP",   color=0xFFFFFF, x=8,  y=16))
    g.append(label.Label(terminalio.FONT, text="TALL: DOWN", color=0x00FFCC, x=2,  y=25))
    display.root_group = g
    display.refresh()
    # Drain any stale button state — the click that entered game mode may still
    # be in the debouncer's pipeline. Wait for all buttons released and call
    # update() a couple extra times to consume any pending .fell events.
    while not button_up.value or not button_down.value or not ext_button.value:
        button_up.update(); button_down.update(); ext_button.update()
        time.sleep(0.01)
    for _ in range(3):
        button_up.update(); button_down.update(); ext_button.update()
        time.sleep(0.01)
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_down.fell:
            return True
        if ext_button.fell or button_up.fell:
            return False
        time.sleep(0.02)


def show_stats_screen(display, score, stats, button_up, button_down, ext_button):
    """Show the post-game stats screen until any button is pressed.

    Always renders in landscape so the player can read labels upright.
    terminalio.FONT character cells are ~8 px tall; four lines at y=5,12,19,26
    (7 px steps) fit the 32 px display but share ~1 px between adjacent rows.
    See PIXEL_FONT.md if you want gap-free hand-drawn text here instead.
    """
    start_round(display, portrait=False)
    new_best = score > 0 and score >= stats["high_score"]
    g = displayio.Group()
    g.append(label.Label(terminalio.FONT,
        text="NEW BEST!" if new_best else "- STATS -",
        color=0xFF6600 if new_best else 0xFFD700, x=4, y=5))
    g.append(label.Label(terminalio.FONT,
        text=f"SCORE {score}", color=0xFFFFFF, x=4, y=12))
    g.append(label.Label(terminalio.FONT,
        text=f"BEST  {stats['high_score']}", color=0x00FFCC, x=4, y=19))
    g.append(label.Label(terminalio.FONT,
        text=f"RUNS  {stats['games_played']}", color=0x00FF00, x=4, y=26))
    display.root_group = g
    display.refresh()
    # Wait for the OOF!-dismiss click to be released before listening for a fresh click
    while not button_up.value or not button_down.value or not ext_button.value:
        button_up.update(); button_down.update(); ext_button.update()
        time.sleep(0.01)
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell or ext_button.fell:
            break
        time.sleep(0.02)


# ── MAIN GAME LOOP ────────────────────────────────────────────────────────────

def run(display, button_up, button_down, ext_button):
    """Run Silly Bird from the mode picker through games until the player exits.

    The game runs in two nested loops:
      outer loop  — one full game (bird moves, pipes scroll, score counts)
      inner reads — buttons checked every frame (~20 FPS)

    Mode is chosen once via MODE? screen on entry. The only exit from game
    mode is the RESET button — crashing just starts another round.
    """
    print("Launching Silly Bird...")

    # Wait for any buttons still held by the launcher to be released
    while not button_up.value or not button_down.value or not ext_button.value:
        button_up.update(); button_down.update(); ext_button.update()
        time.sleep(0.01)

    # Session stats — kept in RAM only, never written to disk
    stats = {"high_score": 0, "games_played": 0}

    # Pick orientation once on entry — UP/EXT = landscape, DOWN = portrait
    portrait = show_mode_picker(display, button_up, button_down, ext_button)
    print(f"Silly Bird — {'portrait' if portrait else 'landscape'}")

    while True:  # outer loop: game → stats → next game
        start_round(display, portrait)
        # Clear any leftover labels (e.g. OOF! from the previous round)
        lbl.hidden  = True
        lbl2.hidden = True

        # ── Game loop ─────────────────────────────────────────────────────────
        # Set up a fresh game: bird floats at the middle and we pre-spawn one
        # "intro" pipe positioned AROUND the bird — bird is inside the gap.
        # As the round starts the pipe scrolls left and the bird ends up past
        # it, with the first real challenge pipe spawning normally from the
        # right edge. This sets the scene without forcing an instant crash.
        bird_y       = float(mode.ground_y // 2)
        bird_v       = 0.0
        centered_gap = int(bird_y) - (mode.pipe_gap - mode.bird_height) // 2
        gap_min      = 4
        gap_max      = mode.ground_y - mode.pipe_gap - 4
        intro_gap_y  = max(gap_min, min(gap_max, centered_gap))
        # Intro pipe is at the bird's x with the gap centered on the bird —
        # the pipe surrounds the bird, no collision. As it scrolls left it
        # auto-scores +1 a few frames in (a freebie welcome point — leaving
        # it in keeps the code simpler and this is a fun game, not a contest).
        pipes        = [Pipe(float(mode.bird_x), intro_gap_y)]
        score        = 0
        spd          = mode.start_speed
        dist         = float(mode.virtual_width)
        puffs        = []
        climb_flap_count = 0

        while True:
            button_up.update(); button_down.update(); ext_button.update()
            # Any button press is a flap; consecutive climbing flaps spawn puffs
            if button_up.fell or button_down.fell or ext_button.fell:
                if bird_v < 0:
                    climb_flap_count += 1
                    if climb_flap_count > 1:
                        is_fire = (climb_flap_count % 3 == 0)
                        puffs.append(Puff(mode.bird_x - 2, int(bird_y) + 1, is_fire))
                        bird_v = DOUBLE_FLAP   # double-jump boost when the tail fires
                    else:
                        bird_v = mode.flap_power
                else:
                    climb_flap_count = 0
                    bird_v = mode.flap_power

            # Physics: gravity pulls the bird down each frame
            bird_v += mode.gravity
            bird_y += bird_v

            # Stop the bird from going through the ceiling or the ground
            if bird_y < 0:
                bird_y = 0.0
                bird_v = 0.0
            if bird_y + mode.bird_height >= mode.ground_y:
                bird_y = float(mode.ground_y - mode.bird_height)
                bird_v = 0.0

            # Pipes only scroll when the bird is alive (in the air)
            if bird_y + mode.bird_height < mode.ground_y:
                dist -= spd
                if dist <= 0:
                    # Time to spawn a new pipe with a random gap height
                    dist = float(mode.virtual_width)
                    gy = random.randint(4, mode.ground_y - mode.pipe_gap - 4)
                    pipes.append(Pipe(float(mode.virtual_width), gy))
                kept = []
                for pipe in pipes:
                    pipe.x -= spd
                    # Score when the bird's left edge passes the pipe's right edge
                    if not pipe.scored and pipe.x + mode.pipe_width < mode.bird_x:
                        pipe.scored = True
                        score += 1
                        spd = mode.start_speed + score * SPEED_UP
                    if pipe.x > -mode.pipe_width - 2:
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

            time.sleep(FRAME_DELAY)   # ~20 FPS at 0.05s

        # ── Game over ─────────────────────────────────────────────────────────
        # Show "OOF!" overlaid on the crash frame.  display.rotation already
        # matches the round's orientation, so the label appears upright in
        # both landscape and portrait — we just position it in the right plane.
        lbl.text   = "OOF!"
        lbl.color  = 0xFF2200
        if mode.portrait:
            lbl.x, lbl.y = 4, 30   # ~centered on the 32×64 portrait plane
        else:
            lbl.x, lbl.y = 20, 13  # ~centered on the 64×32 landscape plane
        lbl.hidden = False
        lbl2.hidden = True
        display.refresh()

        # Update stats and announce the result over USB serial
        stats["games_played"] += 1
        if score > stats["high_score"]:
            stats["high_score"] = score
        print(f"Silly Bird — score: {score}  best: {stats['high_score']}  runs: {stats['games_played']}")

        # Wait for the crash-causing flap to be released, then for a fresh
        # click to dismiss OOF! — otherwise tap-spam would skip the OOF! screen.
        while not button_up.value or not button_down.value or not ext_button.value:
            button_up.update(); button_down.update(); ext_button.update()
            time.sleep(0.01)
        while True:
            button_up.update(); button_down.update(); ext_button.update()
            if button_up.fell or button_down.fell or ext_button.fell:
                break
            time.sleep(0.02)

        show_stats_screen(display, score, stats, button_up, button_down, ext_button)
        # loop back to a new round in the same mode
