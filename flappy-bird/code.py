"""
Flappy Bird for Adafruit Matrix Portal M4
64x32 RGB LED Matrix — CircuitPython 10

Copy this file to the root of your CIRCUITPY drive as code.py.
Press the UP or DOWN button to flap.
"""
import time
import board
import displayio
import rgbmatrix
import framebufferio
import digitalio
import random
import bitmaptools
from adafruit_display_text import label
import terminalio

# ── Display ──────────────────────────────────────────────────────────────
W, H = 64, 32
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=W, height=H, bit_depth=4,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE,
)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

# 10-colour palette
SKY, GND, PIPE, CAP, YELLOW, WHITE, BLACK, CYAN = range(8)
GREY = 8   # smoke puff
FIRE = 9   # fire puff (every 3rd consecutive climbing flap)
pal = displayio.Palette(10)
pal[SKY]    = 0x001040   # dark blue sky
pal[GND]    = 0x7A5C1E   # brown ground
pal[PIPE]   = 0x00AA00   # green pipe body
pal[CAP]    = 0x007700   # darker green pipe cap
pal[YELLOW] = 0xFFD700   # bird body
pal[WHITE]  = 0xFFFFFF   # bird eye white
pal[BLACK]  = 0x000000   # bird pupil / flash
pal[CYAN]   = 0x00FFCC   # score digits
pal[GREY]   = 0x888888   # smoke puff
pal[FIRE]   = 0xFF6600   # fire puff

bmp = displayio.Bitmap(W, H, 16)
tg  = displayio.TileGrid(bmp, pixel_shader=pal)

# Root display group: bitmap layer + text overlay
grp = displayio.Group()
grp.append(tg)
lbl = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF)
grp.append(lbl)
display.root_group = grp

# ── Buttons (active-low) ──────────────────────────────────────────────────
_b_up = digitalio.DigitalInOut(board.BUTTON_UP)
_b_up.switch_to_input(pull=digitalio.Pull.UP)
_b_dn = digitalio.DigitalInOut(board.BUTTON_DOWN)
_b_dn.switch_to_input(pull=digitalio.Pull.UP)

def any_pressed():
    return not _b_up.value or not _b_dn.value

def wait_press_release():
    while not any_pressed():
        time.sleep(0.02)
    while any_pressed():
        time.sleep(0.02)

# ── Game constants ────────────────────────────────────────────────────────
GY   = 27     # y-coordinate of ground top edge
BX   = 10     # bird fixed x position
BW   = 4      # bird sprite width
BH   = 3      # bird sprite height
PW   = 5      # pipe width in pixels
GAP  = 9      # vertical gap between top and bottom pipe
GRAV = 0.32   # downward acceleration per frame
FLAP = -2.7   # upward velocity on button press
SPD0 = 1.0    # starting pipe scroll speed (px/frame)

# ── 3×5 pixel digit font ──────────────────────────────────────────────────
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

# ── Drawing helpers ───────────────────────────────────────────────────────
def box(x, y, w, h, c):
    """Fast rectangle fill via bitmaptools (C-level, clips to display bounds)."""
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(W, x + w)
    y2 = min(H, y + h)
    if x2 > x1 and y2 > y1:
        bitmaptools.fill_region(bmp, x1, y1, x2, y2, c)

def dot(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        bmp[x, y] = c

def draw_score(n):
    x = 1
    for ch in str(n):
        rows = _DIGITS[int(ch)]
        for r, bits in enumerate(rows):
            for b in range(3):
                if bits & (1 << (2 - b)):
                    dot(x + b, 1 + r, CYAN)
        x += 4

def draw_bird(by, bird_v=0.0):
    by = int(by)
    box(BX, by, BW, BH, YELLOW)
    dot(BX + 3, by,     WHITE)   # eye white
    dot(BX + 3, by + 1, BLACK)   # pupil
    # Wing pixel animates with velocity: up when climbing, down when falling
    if bird_v < -1.0:
        dot(BX + 1, by - 1, YELLOW)              # wing up
    elif bird_v > 0.5 and by + BH < GY:
        dot(BX + 1, by + BH, YELLOW)             # wing down

def draw_puff(puff):
    x, y, age, is_fire = puff[0], puff[1], puff[2], puff[3]
    c = FIRE if is_fire else GREY
    if age == 0:                         # fresh: 3-pixel Y-cluster
        dot(x,     y,     c)
        dot(x - 1, y - 1, c)
        dot(x - 1, y + 1, c)
    else:                                # age 1: single fading pixel
        dot(x - 2, y, c)

def draw_pipe(px, gy):
    px = int(px)
    # Top pipe: body + cap on its bottom edge
    if gy > 2:
        box(px, 0, PW, gy - 2, PIPE)
    if gy > 0:
        box(px - 1, gy - 2, PW + 2, 2, CAP)
    # Bottom pipe: cap on its top edge + body below
    bot = gy + GAP
    if bot < GY:
        box(px - 1, bot, PW + 2, 2, CAP)
    if bot + 2 < GY:
        box(px, bot + 2, PW, GY - bot - 2, PIPE)

def draw_scene():
    box(0, 0, W, GY, SKY)
    box(0, GY, W, H - GY, GND)

# ── Collision detection ───────────────────────────────────────────────────
def collides(by, pipes):
    by = int(by)
    if by < 0 or by + BH > GY:          # ceiling or ground
        return True
    for p in pipes:
        px = int(p[0])
        gy = p[1]
        if BX + BW > px and BX < px + PW:   # horizontal overlap
            if by < gy or by + BH > gy + GAP:
                return True
    return False

# ── Screens ───────────────────────────────────────────────────────────────
def show_title():
    draw_scene()
    draw_pipe(44, 8)
    draw_pipe(30, 14)
    draw_bird(GY // 2 - 1)
    lbl.text   = "FLAP!"
    lbl.color  = 0xFFD700
    lbl.x, lbl.y = 17, 8    # centred horizontally, upper third
    lbl.hidden = False
    display.refresh()

def show_dead(score):
    lbl.text   = "DEAD"
    lbl.color  = 0xFF2200
    lbl.x, lbl.y = 20, 16   # centred on screen
    lbl.hidden = False
    # Flash the screen 3 times then settle on final score
    for _ in range(3):
        draw_scene()
        draw_score(score)
        display.refresh()
        time.sleep(0.22)
        box(0, 0, W, H, BLACK)
        display.refresh()
        time.sleep(0.13)
    draw_scene()
    draw_score(score)
    display.refresh()
    time.sleep(0.8)

# ── Main game loop ────────────────────────────────────────────────────────
def play():
    bird_y           = float(GY // 2)
    bird_v           = 0.0
    pipes            = []          # each entry: [x, gap_y, scored_flag]
    score            = 0
    spd              = SPD0
    dist             = 32.0        # pixels until next pipe spawns
    puffs            = []          # [x, y, age, is_fire]
    climb_flap_count = 0
    prev             = any_pressed()
    lbl.hidden       = True

    while True:
        cur = any_pressed()
        if cur and not prev:
            if bird_v < 0:              # already climbing → smoke or fire
                climb_flap_count += 1
                if climb_flap_count > 1:
                    is_fire = (climb_flap_count % 3 == 0)
                    puffs.append([BX - 2, int(bird_y) + 1, 0, is_fire])
            else:
                climb_flap_count = 0
            bird_v = FLAP
        prev = cur

        # Physics
        bird_v += GRAV
        bird_y += bird_v

        # Spawn pipes
        dist -= spd
        if dist <= 0:
            dist = 32.0
            gy = random.randint(4, GY - GAP - 4)
            pipes.append([float(W), gy, False])

        # Scroll pipes, award score when pipe clears bird
        kept = []
        for p in pipes:
            p[0] -= spd
            if not p[2] and p[0] + PW < BX:
                p[2] = True
                score += 1
                spd = SPD0 + score * 0.08   # gradually speed up
            if p[0] > -PW - 2:
                kept.append(p)
        pipes = kept

        # Draw frame
        draw_scene()
        for p in pipes:
            draw_pipe(p[0], p[1])
        alive = []
        for p in puffs:
            draw_puff(p)
            p[2] += 1
            if p[2] < 2:
                alive.append(p)
        puffs = alive
        draw_bird(bird_y, bird_v)
        draw_score(score)
        display.refresh()

        if collides(bird_y, pipes):
            return score

        time.sleep(0.05)   # ~20 FPS

# ── Entry point ───────────────────────────────────────────────────────────
show_title()
wait_press_release()

while True:
    final_score = play()
    show_dead(final_score)
    wait_press_release()
    show_title()
    wait_press_release()
