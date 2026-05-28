"""
Matrix Portal M4 — Silly Bird
Flappy Bird-style game for the 64×32 LED matrix.
Public API: run(display, button_up, button_down, ext_button)
Loops instructions → ready → game → stats until DOWN is pressed on the title screen.
Stats are kept in RAM only; nothing is written to the file system.

Portrait mode maps a virtual 32×64 game space onto the 64×32 physical display
via a 90° CW coordinate rotation.  Hold the Matrix Portal with its 64-pixel
axis vertical and USB port at the bottom to play in portrait orientation.

Transform: virtual (vx, vy) → physical (px=vy, py=virtual_width-1-vx)
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
BIRD_X        = 10     # bird's fixed horizontal position (virtual coords)
GROUND_Y      = 27     # y-coordinate of the ground in landscape mode

FRAME_DELAY   = 0.05   # seconds between frames     (smaller = faster game)

# Portrait orientation overrides (hold device tall-side up, USB at bottom).
# Portrait has a taller play area, so the gap and pipe width differ — but
# the bird's flap arc is the same number of pixels in both modes.
PORTRAIT_PIPE_GAP   = 14
PORTRAIT_PIPE_WIDTH = 3
PORTRAIT_GROUND_Y   = 56   # ground sits ~87% down the 64-tall virtual space


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

# Physical display is always 64×32 — portrait is a coordinate transform,
# not a rotation of the underlying bitmap.
PHYS_W = 64
PHYS_H = 32

bmp  = displayio.Bitmap(PHYS_W, PHYS_H, 16)
grp  = displayio.Group()
grp.append(displayio.TileGrid(bmp, pixel_shader=palette))
lbl  = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF)
grp.append(lbl)
lbl2 = label.Label(terminalio.FONT, text=" ", color=0xAAAAAA)
lbl2.hidden = True
grp.append(lbl2)


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
        self.bird_x      = BIRD_X
        self.bird_width  = BIRD_WIDTH
        self.bird_height = BIRD_HEIGHT
        self.gravity     = GRAVITY
        self.flap_power  = FLAP_POWER
        self.start_speed = START_SPEED
        if portrait:
            # Virtual space is 32 wide × 64 tall — taller play area
            self.virtual_width  = 32
            self.virtual_height = 64
            self.ground_y       = PORTRAIT_GROUND_Y
            self.pipe_width     = PORTRAIT_PIPE_WIDTH
            self.pipe_gap       = PORTRAIT_PIPE_GAP
        else:
            # Landscape: virtual space matches the physical 64×32 display
            self.virtual_width  = 64
            self.virtual_height = 32
            self.ground_y       = GROUND_Y
            self.pipe_width     = PIPE_WIDTH
            self.pipe_gap       = PIPE_GAP


class Pipe:
    """One scrolling pipe pair (top + bottom with a gap in the middle)."""
    def __init__(self, x, gap_y):
        self.x      = x          # virtual x-coordinate of the pipe's left edge
        self.gap_y  = gap_y      # virtual y-coordinate of the top of the gap
        self.scored = False      # True once the bird has flown past this pipe


class Puff:
    """A trailing smoke or fire puff behind the bird."""
    def __init__(self, x, y, is_fire):
        self.x       = x
        self.y       = y
        self.age     = 0         # frames since the puff was spawned
        self.is_fire = is_fire   # fire puff every 3rd chain-flap, smoke otherwise


# Current game mode — replaced by start_round() before each round.
# Drawing helpers below read this single object instead of 13 separate globals.
mode = GameMode(portrait=False)


def start_round(portrait):
    """Set up landscape or portrait settings for the next round."""
    global mode
    mode = GameMode(portrait)


# ── COORDINATE TRANSFORM HELPERS ──────────────────────────────────────────────
# The display is always 64 wide × 32 tall.  In portrait mode we pretend the
# game world is 32 wide × 64 tall and rotate every pixel 90° clockwise when
# drawing.  That lets the same game code work for both orientations.
#
# Portrait transform: virtual (vx, vy) → physical (px = vy, py = virtual_width - 1 - vx)

def box(vx, vy, vw, vh, color_index):
    """Fill a rectangle in virtual coords, rotating into portrait if needed."""
    if mode.portrait:
        # 90° CW: virtual rect → physical rect via px=vy, py=virtual_width-1-vx
        vw_total = mode.virtual_width
        x1 = max(0, vy);                     x2 = min(PHYS_W, vy + vh)
        y1 = max(0, vw_total - vx - vw);     y2 = min(PHYS_H, vw_total - vx)
    else:
        x1 = max(0, vx);  x2 = min(PHYS_W, vx + vw)
        y1 = max(0, vy);  y2 = min(PHYS_H, vy + vh)
    if x2 > x1 and y2 > y1:
        bitmaptools.fill_region(bmp, x1, y1, x2, y2, color_index)


def dot(vx, vy, color_index):
    """Set a single pixel in virtual coords, rotating into portrait if needed."""
    if mode.portrait:
        px, py = vy, mode.virtual_width - 1 - vx
    else:
        px, py = vx, vy
    if 0 <= px < PHYS_W and 0 <= py < PHYS_H:
        bmp[px, py] = color_index


# ── DRAWING FUNCTIONS ─────────────────────────────────────────────────────────

def draw_score(n):
    """Draw the current score in the top-left corner."""
    # In portrait we write directly in physical coords so the digits read upright.
    if mode.portrait:
        x = 2
        for ch in str(n):
            for row_idx, row in enumerate(DIGITS[int(ch)]):
                for col_idx, glyph in enumerate(row):
                    if glyph == '#':
                        px, py = x + col_idx, 1 + row_idx
                        if 0 <= px < PHYS_W and 0 <= py < PHYS_H:
                            bmp[px, py] = CYN
            x += 4
    else:
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
    box(0, 0,              mode.virtual_width, mode.ground_y,                          SKY)
    box(0, mode.ground_y,  mode.virtual_width, mode.virtual_height - mode.ground_y,   GND)


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


# Instructions are shown once per power-on, not once per run() call.
instructions_shown = False


# ── SCREEN FUNCTIONS ──────────────────────────────────────────────────────────

def show_instructions(display, button_up, button_down, ext_button):
    """Show the controls cheat-sheet until any button is pressed."""
    g = displayio.Group()
    # Title-screen controls
    g.append(label.Label(terminalio.FONT, text="WIDE/TALL", color=0x888888, x=2, y=5))
    # In-game: any button flaps; EXT starts a new game from the title screen too
    g.append(label.Label(terminalio.FONT, text="TAP=FLAP",  color=0x00FFCC, x=2, y=16))
    g.append(label.Label(terminalio.FONT, text="EXT=PLAY",  color=0xFF6600, x=2, y=25))
    display.root_group = g
    display.refresh()
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell or ext_button.fell:
            break
        time.sleep(0.02)


def show_quit_confirm(display, button_up, button_down, ext_button):
    """Ask the player to confirm quitting; return True to quit, False to resume.

    EXT = keep playing (back to title) so clicker-only players never get stuck.
    UP or DOWN = exit game mode back to the hub.
    """
    g = displayio.Group()
    g.append(label.Label(terminalio.FONT, text="QUIT?",    color=0xFF2200, x=16, y=5))
    g.append(label.Label(terminalio.FONT, text="UP/DN=HUB",color=0xFF6600, x=1,  y=16))
    g.append(label.Label(terminalio.FONT, text="EXT=PLAY", color=0x00FFCC, x=4,  y=25))
    display.root_group = g
    display.refresh()
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell:
            return True    # exit to hub
        if ext_button.fell:
            return False   # keep playing — go back to title
        time.sleep(0.02)


def show_stats_screen(display, score, stats, button_up, button_down, ext_button):
    """Show the post-game stats screen until any button is pressed.

    Always renders in landscape so the player can read labels upright.
    terminalio.FONT character cells are ~8 px tall; four lines at y=5,12,19,26
    (7 px steps) fit the 32 px display but share ~1 px between adjacent rows.
    See PIXEL_FONT.md if you want gap-free hand-drawn text here instead.
    """
    start_round(portrait=False)
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
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell or ext_button.fell:
            break
        time.sleep(0.02)


# ── MAIN GAME LOOP ────────────────────────────────────────────────────────────

def run(display, button_up, button_down, ext_button):
    """Run Silly Bird from ready screen through games until the player exits.

    The game runs in three nested loops:
      outer loop  — ready screen → pick orientation
      middle loop — one full game (bird moves, pipes scroll, score counts)
      inner reads — buttons checked every frame (~20 FPS)

    Ready-screen controls:
      UP   → play landscape (64×32 wide)
      DOWN → play portrait (32×64 tall — hold device long-side up, USB at bottom)
      EXT  → play in the currently-selected mode
    To exit game mode: hold UP+DOWN together to bring up QUIT_CONFIRM.
    """
    global instructions_shown

    print("Launching Silly Bird...")

    # Wait for any buttons still held by the launcher to be released
    while not button_up.value or not button_down.value or not ext_button.value:
        button_up.update(); button_down.update(); ext_button.update()
        time.sleep(0.01)

    # Session stats — kept in RAM only, never written to disk
    stats = {"high_score": 0, "games_played": 0}

    # Show controls once per power-on (not on every re-entry from the hub)
    if not instructions_shown:
        show_instructions(display, button_up, button_down, ext_button)
        instructions_shown = True

    portrait = False   # remembered across rounds — sticks to last chosen mode

    while True:  # outer loop: ready → game → stats → ready
        # ── Ready state: draw the game scene and wait for first input ─────────
        # No separate title screen — the game scene IS the menu.
        start_round(portrait)
        display.root_group = grp
        draw_scene()
        draw_bird(float(mode.ground_y // 2))

        # Mode hint at the bottom — only in landscape; in portrait the labels
        # would read sideways, and the rotated game scene speaks for itself.
        if not portrait:
            lbl.text      = "UP:WIDE"
            lbl.color     = 0xFFFFFF
            lbl.x, lbl.y  = 1, 22
            lbl.hidden    = False
            lbl2.text     = "DN:TALL"
            lbl2.color    = 0x555555
            lbl2.x, lbl2.y = 1, 29
            lbl2.hidden   = False
        else:
            lbl.hidden  = True
            lbl2.hidden = True
        display.refresh()

        while True:
            button_up.update(); button_down.update(); ext_button.update()
            if ext_button.fell:
                break                   # play in current mode
            if button_up.fell:
                portrait = False
                start_round(False)
                break
            if button_down.fell:
                portrait = True
                start_round(True)
                break
            time.sleep(0.02)

        lbl.hidden = lbl2.hidden = True
        print(f"Silly Bird — {'portrait' if portrait else 'landscape'}")

        # ── Game loop ─────────────────────────────────────────────────────────
        # Set up a fresh game: bird floats at the middle, no pipes yet
        bird_y           = float(mode.ground_y // 2)
        bird_v           = 0.0
        pipes            = []
        score            = 0
        spd              = mode.start_speed
        dist             = float(mode.virtual_width)   # first pipe appears after one virtual-width of scroll
        puffs            = []
        climb_flap_count = 0
        quit_game        = False

        while True:
            button_up.update(); button_down.update(); ext_button.update()
            # Both bird buttons held at once → ask before quitting
            if not button_up.value and not button_down.value:
                if show_quit_confirm(display, button_up, button_down, ext_button):
                    quit_game = True
                    break
                # Player chose to resume — restore the game display
                display.root_group = grp
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
        if quit_game:
            continue    # loop back to ready screen (stay in game mode)

        # Show "OOF!" over the crash frame.  Post-game screens always render
        # in landscape (labels can't be rotated), so we switch coords and
        # repaint the background before adding the label.  If the round was
        # portrait, also show "TILT" so the player knows to rotate the device.
        was_portrait = mode.portrait
        start_round(portrait=False)
        draw_scene()   # clear portrait bitmap content so OOF! has a clean background
        lbl.text   = "OOF!"
        lbl.color  = 0xFF2200
        lbl.x, lbl.y = 20, 13
        lbl.hidden = False
        lbl2.text    = "TILT" if was_portrait else " "
        lbl2.color   = 0x888888
        lbl2.x, lbl2.y = 20, 24
        lbl2.hidden  = False
        display.refresh()

        # Update stats and announce the result over USB serial
        stats["games_played"] += 1
        if score > stats["high_score"]:
            stats["high_score"] = score
        print(f"Silly Bird — score: {score}  best: {stats['high_score']}  runs: {stats['games_played']}")

        # Wait for any click to dismiss OOF! — goes straight to stats
        while True:
            button_up.update(); button_down.update(); ext_button.update()
            if button_up.fell or button_down.fell or ext_button.fell:
                break
            time.sleep(0.02)

        show_stats_screen(display, score, stats, button_up, button_down, ext_button)
        # loop back to ready screen
