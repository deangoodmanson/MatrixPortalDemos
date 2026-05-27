"""
Matrix Portal M4 — Silly Bird
Flappy Bird-style game for the 64×32 LED matrix.
Public API: run(display, button_up, button_down, ext_button)
Loops instructions→title→game→stats until DOWN is pressed on the title screen.
Stats are kept in RAM only; nothing is written to the file system.

Portrait mode maps a virtual 32×64 game space onto the 64×32 physical display
via a 90° CW coordinate rotation.  Hold the Matrix Portal with its 64-pixel
axis vertical and USB port at the bottom to play in portrait orientation.

Transform: virtual (vx, vy) → physical (px=vy, py=31-vx)
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

GRAVITY       = 0.18   # how fast the bird falls   (bigger = falls faster)
FLAP_POWER    = -1.1   # how high one flap goes    (more negative = stronger flap)
PIPE_GAP      = 9      # pixels between top/bottom pipe  (bigger = easier)
PIPE_WIDTH    = 5      # how wide each pipe is
START_SPEED   = 1.0    # pipe scroll speed at game start
SPEED_UP      = 0.08   # extra speed gained per pipe cleared

BIRD_WIDTH    = 4      # bird hitbox width in pixels
BIRD_HEIGHT   = 3      # bird hitbox height in pixels
BIRD_X        = 10     # bird's fixed horizontal position (virtual coords)
GROUND_Y      = 27     # y-coordinate of the ground in landscape mode

FRAME_DELAY   = 0.05   # seconds between frames  (smaller = faster game, ~20 FPS at 0.05)

# Portrait orientation overrides (hold device tall-side up, USB at bottom)
# Portrait has a taller play area, so it needs a stronger flap and bigger gap.
PORTRAIT_FLAP_POWER = -1.8
PORTRAIT_PIPE_GAP   = 14
PORTRAIT_PIPE_WIDTH = 3
PORTRAIT_GROUND_Y   = 56   # ground sits ~87% down the 64-tall virtual space


# ── COLORS ────────────────────────────────────────────────────────────────────
# Each color is a 24-bit hex value: 0xRRGGBB
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
COLOR_FIRE   = 0xFF6600   # orange fire puff (every 3rd consecutive climbing flap)


# ── PALETTE / DISPLAY SETUP ───────────────────────────────────────────────────
# A palette is a small lookup table: each pixel stores an index (0–9) and the
# palette converts that index into a real RGB color when the matrix is drawn.

_SKY, _GND, _PIPE, _CAP, _YEL, _WHT, _BLK, _CYN = range(8)
_GREY = 8   # smoke puff index
_FIRE = 9   # fire puff index

_pal = displayio.Palette(10)
_pal[_SKY]  = COLOR_SKY
_pal[_GND]  = COLOR_GROUND
_pal[_PIPE] = COLOR_PIPE
_pal[_CAP]  = COLOR_CAP
_pal[_YEL]  = COLOR_BIRD
_pal[_WHT]  = COLOR_WHITE
_pal[_BLK]  = COLOR_BLACK
_pal[_CYN]  = COLOR_SCORE
_pal[_GREY] = COLOR_SMOKE
_pal[_FIRE] = COLOR_FIRE

# Physical display is always 64×32 — portrait is a coordinate transform, not a rotation
_PHYS_W = 64
_PHYS_H = 32

_bmp = displayio.Bitmap(_PHYS_W, _PHYS_H, 16)
_tg   = displayio.TileGrid(_bmp, pixel_shader=_pal)
_grp  = displayio.Group()
_grp.append(_tg)
_lbl  = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF)
_grp.append(_lbl)
_lbl2 = label.Label(terminalio.FONT, text=" ", color=0xAAAAAA)   # mode hint on title
_lbl2.hidden = True
_grp.append(_lbl2)


# ── SCORE DIGIT BITMAPS ───────────────────────────────────────────────────────
# Each digit is a 3-wide × 5-tall grid.  Each row is a 3-bit number where 1=on.
# For example, 0b101 means: ON, off, ON (the left and right pixels are lit).

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


# ── COORDINATE TRANSFORM HELPERS ──────────────────────────────────────────────
# The display is always 64 wide × 32 tall.  In portrait mode we pretend the
# game world is 32 wide × 64 tall and rotate every pixel 90° clockwise when
# drawing.  That lets the same game code work for both orientations.
#
# Portrait transform: virtual (vx, vy) → physical (px = vy, py = VW - 1 - vx)

# Orientation-dependent game state — set by _init_mode()
_portrait = False
_VW   = 64      # virtual width
_VH   = 32      # virtual height
_GY   = GROUND_Y
_BX   = BIRD_X
_BW   = BIRD_WIDTH
_BH   = BIRD_HEIGHT
_PW   = PIPE_WIDTH
_GAP  = PIPE_GAP
_GRAV = GRAVITY
_FLAP = FLAP_POWER
_SPD0 = START_SPEED


def _init_mode(portrait):
    """Pick landscape or portrait game constants for this round."""
    # portrait maps a 32×64 virtual game onto the 64×32 physical display by rotating coordinates
    global _portrait, _VW, _VH, _GY, _BX, _BW, _BH, _PW, _GAP, _GRAV, _FLAP, _SPD0
    _portrait = portrait
    _BW, _BH = BIRD_WIDTH, BIRD_HEIGHT
    if portrait:
        # Virtual space is 32 wide × 64 tall — taller play area
        _VW, _VH = 32, 64
        _GY   = PORTRAIT_GROUND_Y
        _BX   = BIRD_X
        _PW   = PORTRAIT_PIPE_WIDTH
        _GAP  = PORTRAIT_PIPE_GAP
        _GRAV = GRAVITY
        _FLAP = PORTRAIT_FLAP_POWER
        _SPD0 = START_SPEED
    else:
        # Landscape: virtual space matches the physical 64×32 display
        _VW, _VH = 64, 32
        _GY   = GROUND_Y
        _BX   = BIRD_X
        _PW   = PIPE_WIDTH
        _GAP  = PIPE_GAP
        _GRAV = GRAVITY
        _FLAP = FLAP_POWER
        _SPD0 = START_SPEED


def _box(vx, vy, vw, vh, c):
    """Fill a rectangle in virtual coords, rotating into portrait if needed."""
    if _portrait:
        # 90° CW: virtual rect → physical rect via px=vy, py=VW-1-vx
        x1 = max(0, vy);         x2 = min(_PHYS_W, vy + vh)
        y1 = max(0, _VW - vx - vw); y2 = min(_PHYS_H, _VW - vx)
    else:
        x1 = max(0, vx);         x2 = min(_PHYS_W, vx + vw)
        y1 = max(0, vy);         y2 = min(_PHYS_H, vy + vh)
    if x2 > x1 and y2 > y1:
        bitmaptools.fill_region(_bmp, x1, y1, x2, y2, c)


def _dot(vx, vy, c):
    """Set a single pixel in virtual coords, rotating into portrait if needed."""
    if _portrait:
        px, py = vy, _VW - 1 - vx
    else:
        px, py = vx, vy
    if 0 <= px < _PHYS_W and 0 <= py < _PHYS_H:
        _bmp[px, py] = c


# ── DRAWING FUNCTIONS ─────────────────────────────────────────────────────────

def _draw_score(n):
    """Draw the current score in the top-left corner."""
    # In portrait we write directly in physical coords so the digits read upright.
    if _portrait:
        x = 2
        for ch in str(n):
            rows = _DIGITS[int(ch)]
            for r, bits in enumerate(rows):
                for b in range(3):
                    if bits & (1 << (2 - b)):
                        px, py = x + b, 1 + r
                        if 0 <= px < _PHYS_W and 0 <= py < _PHYS_H:
                            _bmp[px, py] = _CYN
            x += 4
    else:
        x = 1
        for ch in str(n):
            rows = _DIGITS[int(ch)]
            for r, bits in enumerate(rows):
                for b in range(3):
                    if bits & (1 << (2 - b)):
                        _dot(x + b, 1 + r, _CYN)
            x += 4


def _draw_bird(by, bird_v=0.0):
    """Draw the bird at vertical position by, with a tiny wing flick when moving."""
    by = int(by)
    _box(_BX + 1, by,     2, 1, _YEL)
    _dot(_BX,     by + 1, _YEL)
    _dot(_BX + 1, by + 1, _WHT)
    _dot(_BX + 2, by + 1, _BLK)
    _dot(_BX + 3, by + 1, _FIRE)
    _box(_BX,     by + 2, 3, 1, _YEL)
    # A 1-pixel wing tip flips above or below depending on whether we're climbing or diving
    if bird_v < -0.5:
        _dot(_BX + 1, by - 1, _YEL)
    elif bird_v > 0.5 and by + _BH < _GY:
        _dot(_BX + 1, by + _BH, _YEL)


def _draw_puff(puff):
    """Draw a smoke or fire puff trailing behind the bird."""
    x, y, age, is_fire = puff[0], puff[1], puff[2], puff[3]
    c = _FIRE if is_fire else _GREY
    # Young puffs are a small cluster; old puffs shrink to a single trailing dot
    if age == 0:
        _dot(x,     y,     c)
        _dot(x - 1, y - 1, c)
        _dot(x - 1, y + 1, c)
    else:
        _dot(x - 2, y, c)


def _draw_pipe(px, gy):
    """Draw a green pipe with a gap centred at gy."""
    px = int(px)
    # Top pipe: body then darker cap
    if gy > 2:
        _box(px, 0, _PW, gy - 2, _PIPE)
    if gy > 0:
        _box(px - 1, gy - 2, _PW + 2, 2, _CAP)
    # Bottom pipe: cap then body, stopping above the ground
    bot = gy + _GAP
    if bot < _GY:
        _box(px - 1, bot, _PW + 2, 2, _CAP)
    if bot + 2 < _GY:
        _box(px, bot + 2, _PW, _GY - bot - 2, _PIPE)


def _draw_scene():
    """Paint the sky and ground — the background for every frame."""
    _box(0, 0, _VW, _GY, _SKY)
    _box(0, _GY, _VW, _VH - _GY, _GND)


# ── COLLISION DETECTION ───────────────────────────────────────────────────────

def _collides(by, pipes):
    """Return True if the bird's box overlaps any pipe."""
    by = int(by)
    for p in pipes:
        px = int(p[0])
        gy = p[1]
        # Check horizontal overlap first, then vertical (above-gap or below-gap)
        if _BX + _BW > px and _BX < px + _PW:
            if by < gy or by + _BH > gy + _GAP:
                return True
    return False


# Instructions are shown once per power-on, not once per run() call.
_instructions_shown = False


# ── SCREEN FUNCTIONS ──────────────────────────────────────────────────────────

def _show_instructions(display, button_up, button_down, ext_button):
    """Show the controls cheat-sheet until any button is pressed."""
    grp = displayio.Group()
    # Title-screen controls
    grp.append(label.Label(terminalio.FONT, text="UP:W DN:T",  color=0x888888, x=2, y=5))
    # In-game: any button flaps; EXT starts a new game from the title screen too
    grp.append(label.Label(terminalio.FONT, text="TAP=FLAP",   color=0x00FFCC, x=2, y=16))
    grp.append(label.Label(terminalio.FONT, text="EXT=PLAY",   color=0xFF6600, x=2, y=25))
    display.root_group = grp
    display.refresh()
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell or ext_button.fell:
            break
        time.sleep(0.02)


def _show_quit_confirm(display, button_up, button_down, ext_button):
    """Ask the player to confirm quitting; return True to quit, False to resume.

    EXT = keep playing (back to title) so clicker-only players never get stuck.
    UP or DOWN = exit game mode back to the hub.
    """
    grp = displayio.Group()
    grp.append(label.Label(terminalio.FONT, text="QUIT?",    color=0xFF2200, x=16, y=5))
    grp.append(label.Label(terminalio.FONT, text="UP/DN=HUB",color=0xFF6600, x=1,  y=16))
    grp.append(label.Label(terminalio.FONT, text="EXT=PLAY", color=0x00FFCC, x=4,  y=25))
    display.root_group = grp
    display.refresh()
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell:
            return True    # exit to hub
        if ext_button.fell:
            return False   # keep playing — go back to title
        time.sleep(0.02)


def _show_stats_screen(display, score, stats, button_up, button_down, ext_button):
    """Show the post-game stats screen until any button is pressed."""
    # "NEW BEST!" celebrates whenever this run ties or beats the session high
    new_best = score > 0 and score >= stats["high_score"]
    grp = displayio.Group()
    # terminalio.FONT renders ~7px tall per line; y is the top of the cell.
    # y=1 avoids the 1-pixel top-clip on capital letters; 7px spacing = tight stack.
    grp.append(label.Label(terminalio.FONT,
        text="NEW BEST!" if new_best else "- STATS -",
        color=0xFF6600 if new_best else 0xFFD700, x=4, y=1))
    grp.append(label.Label(terminalio.FONT,
        text=f"SCORE {score}", color=0xFFFFFF, x=4, y=9))
    grp.append(label.Label(terminalio.FONT,
        text=f"BEST  {stats['high_score']}", color=0x00FFCC, x=4, y=17))
    grp.append(label.Label(terminalio.FONT,
        text=f"RUNS  {stats['games_played']}", color=0x00FF00, x=4, y=25))
    display.root_group = grp
    display.refresh()
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_up.fell or button_down.fell or ext_button.fell:
            break
        time.sleep(0.02)


# ── MAIN GAME LOOP ────────────────────────────────────────────────────────────

def run(display, button_up, button_down, ext_button):
    """Run Silly Bird from title screen through games until the player exits."""
    # The game runs in three nested loops:
    #   outer loop  — title screen → pick orientation
    #   middle loop — one full game (bird moves, pipes scroll, score counts)
    #   inner reads — buttons checked every frame (~20 FPS)
    #
    # Title-screen controls:
    #   UP   → play landscape (64×32 wide)
    #   DOWN → play portrait (32×64 tall — hold device long-side up, USB at bottom)
    #   EXT  → exit back to the hub (STARTUP_SCREEN)

    global _instructions_shown

    print("Launching Silly Bird...")

    # Wait for any buttons still held by the launcher to be released
    while not button_up.value or not button_down.value or not ext_button.value:
        button_up.update(); button_down.update(); ext_button.update()
        time.sleep(0.01)

    # Session stats — kept in RAM only, never written to disk
    stats = {"high_score": 0, "games_played": 0}

    # Show controls once per power-on (not on every re-entry from the hub)
    if not _instructions_shown:
        _show_instructions(display, button_up, button_down, ext_button)
        _instructions_shown = True

    portrait = False   # remembered across rounds — sticks to last chosen mode

    while True:  # outer loop: title → game → stats → title
        # ── Title screen (always landscape for readability) ───────────────────
        _init_mode(False)               # landscape constants for title draw
        display.root_group = _grp
        _draw_scene()
        _draw_pipe(44, 8)
        _draw_pipe(30, 14)
        _draw_bird(_GY // 2 - 1)

        _lbl.text  = "SILLY!"
        _lbl.color = 0xFFD700
        _lbl.x, _lbl.y = 14, 8
        _lbl.hidden = False

        # Bottom hint: "UP:W DN:T" centred (9 chars × 6px = 54px → x=5)
        _lbl2.text  = "UP:W DN:T"
        _lbl2.color = 0x888888
        _lbl2.x, _lbl2.y = 5, 26
        _lbl2.hidden = False

        display.refresh()

        # Pick a mode: UP/EXT = landscape (wide), DOWN = portrait (tall)
        # portrait is remembered from the previous round — title highlights current choice.
        # EXT starts a game in the current mode so clicker-only players never need device buttons.
        # To exit game mode entirely: hold both UP+DN → QUIT_CONFIRM → UP/DN.
        while True:
            button_up.update(); button_down.update(); ext_button.update()
            if ext_button.fell:
                break            # keep portrait as-is from last round
            if button_up.fell:
                portrait = False
                break
            if button_down.fell:
                portrait = True
                break
            time.sleep(0.02)

        _lbl.hidden = _lbl2.hidden = True
        _init_mode(portrait)
        print(f"Silly Bird — {'portrait' if portrait else 'landscape'}")

        # ── Game loop ─────────────────────────────────────────────────────────
        # Set up a fresh game: bird floats at the middle, no pipes yet
        bird_y           = float(_GY // 2)
        bird_v           = 0.0
        pipes            = []
        score            = 0
        spd              = _SPD0
        dist             = float(_VW)   # first pipe appears after one virtual-width of scroll
        puffs            = []
        climb_flap_count = 0
        quit_game        = False

        while True:
            button_up.update(); button_down.update(); ext_button.update()
            # Both bird buttons held at once → ask before quitting
            if not button_up.value and not button_down.value:
                if _show_quit_confirm(display, button_up, button_down, ext_button):
                    quit_game = True
                    break
                # Player chose to resume — restore the game display
                display.root_group = _grp
            # Any button press is a flap; consecutive climbing flaps spawn puffs
            if button_up.fell or button_down.fell or ext_button.fell:
                if bird_v < 0:
                    climb_flap_count += 1
                    if climb_flap_count > 1:
                        is_fire = (climb_flap_count % 3 == 0)
                        puffs.append([_BX - 2, int(bird_y) + 1, 0, is_fire])
                else:
                    climb_flap_count = 0
                bird_v = _FLAP

            # Physics: gravity pulls the bird down each frame
            bird_v += _GRAV
            bird_y += bird_v

            # Stop the bird from going through the ceiling or the ground
            if bird_y < 0:
                bird_y = 0.0
                bird_v = 0.0
            if bird_y + _BH >= _GY:
                bird_y = float(_GY - _BH)
                bird_v = 0.0

            # Pipes only scroll when the bird is alive (in the air)
            if bird_y + _BH < _GY:
                dist -= spd
                if dist <= 0:
                    # Time to spawn a new pipe with a random gap height
                    dist = float(_VW)
                    gy = random.randint(4, _GY - _GAP - 4)
                    pipes.append([float(_VW), gy, False])
                kept = []
                for p in pipes:
                    p[0] -= spd
                    # Score when the bird's right edge passes the pipe's right edge
                    if not p[2] and p[0] + _PW < _BX:
                        p[2] = True
                        score += 1
                        spd = _SPD0 + score * SPEED_UP
                    if p[0] > -_PW - 2:
                        kept.append(p)
                pipes = kept

            # Redraw the world this frame
            _draw_scene()
            for p in pipes:
                _draw_pipe(p[0], p[1])
            # Age each puff; drop ones older than 1 frame
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

            time.sleep(FRAME_DELAY)   # ~20 FPS at 0.05s

        # ── Game over ─────────────────────────────────────────────────────────
        if quit_game:
            continue    # loop back to title screen (stay in game mode)

        # Show "OOF!" over the crash frame — no black wipe, just overlay the label
        _init_mode(False)   # landscape coords so the label reads upright
        _lbl.text   = "OOF!"
        _lbl.color  = 0xFF2200
        _lbl.x, _lbl.y = 20, 13
        _lbl.hidden = False
        display.refresh()

        # Update stats and announce the result over USB serial
        stats["games_played"] += 1
        if score > stats["high_score"]:
            stats["high_score"] = score
        print(f"Silly Bird — score: {score}  best: {stats['high_score']}  runs: {stats['games_played']}")

        # Wait for any click to dismiss OOF! — goes straight to stats, no TAP screen
        while True:
            button_up.update(); button_down.update(); ext_button.update()
            if button_up.fell or button_down.fell or ext_button.fell:
                break
            time.sleep(0.02)

        _show_stats_screen(display, score, stats, button_up, button_down, ext_button)
        # loop back to title
