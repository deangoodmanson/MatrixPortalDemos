"""
Matrix Portal M4 USB Frame Receiver
Receives RGB565 frame data via USB serial and displays on 64x32 LED matrix.
Achieves ~24 FPS using bitmaptools.arrayblit for C-level memory copy.
"""

import time
import board
import displayio
import rgbmatrix
import framebufferio
import usb_cdc
from adafruit_display_text import label
import terminalio
import digitalio
from adafruit_imageload import load
import struct

import struct
import bitmaptools
import array
import random
from adafruit_debouncer import Debouncer

# Matrix configuration
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 32
MAX_FPS = 30

# Frame data size: 64 * 32 * 2 bytes (RGB565)
FRAME_SIZE = MATRIX_WIDTH * MATRIX_HEIGHT * 2
FRAME_HEADER = b'IMG1'

# Initialize RGB Matrix
displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=MATRIX_WIDTH,
    height=MATRIX_HEIGHT,
    bit_depth=6,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE
)

display = framebufferio.FramebufferDisplay(matrix)

# Create bitmap and group once at startup
# Use a 16-bit bitmap (65536 colors) for RGB565
# Mac sends little-endian RGB565, which we assemble directly in display_frame()
bitmap = displayio.Bitmap(MATRIX_WIDTH, MATRIX_HEIGHT, 65536)
color_converter = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565)

tile_grid = displayio.TileGrid(bitmap, pixel_shader=color_converter)
group = displayio.Group()
group.append(tile_grid)
display.root_group = group

# Setup buttons — all three wrapped in Debouncer for clean edge detection.
# Debouncer.fell  → fires once when button is pressed   (HIGH→LOW, active-low)
# Debouncer.rose  → fires once when button is released  (LOW→HIGH)
# Debouncer.value → current debounced state (False = pressed)
# Requires debouncer.update() to be called every loop iteration.
_pin_up = digitalio.DigitalInOut(board.BUTTON_UP)
_pin_up.switch_to_input(pull=digitalio.Pull.UP)
button_up = Debouncer(_pin_up)

_pin_dn = digitalio.DigitalInOut(board.BUTTON_DOWN)
_pin_dn.switch_to_input(pull=digitalio.Pull.UP)
button_down = Debouncer(_pin_dn)

# External snap / flap button
# ── Wiring ────────────────────────────────────────────────────────────────
#  One side of the momentary switch → A0  pad on the Matrix Portal M4
#  Other side of the switch         → GND pad on the Matrix Portal M4
#
#  Both pads are on the bottom edge of the board, labelled A0 and GND.
#  The 3.3 V pad sits between them and should not be connected to the switch.
#  No external resistor is needed; the internal pull-up is enabled below.
# ─────────────────────────────────────────────────────────────────────────
_pin_ext = digitalio.DigitalInOut(board.A0)
_pin_ext.switch_to_input(pull=digitalio.Pull.UP)
ext_button = Debouncer(_pin_ext)

# ── Flappy Bird resources (created once at startup) ───────────────────────
_FB_SKY, _FB_GND, _FB_PIPE, _FB_CAP, _FB_YEL, _FB_WHT, _FB_BLK, _FB_CYN = range(8)
_fb_pal = displayio.Palette(8)
_fb_pal[_FB_SKY]  = 0x001040
_fb_pal[_FB_GND]  = 0x7A5C1E
_fb_pal[_FB_PIPE] = 0x00AA00
_fb_pal[_FB_CAP]  = 0x007700
_fb_pal[_FB_YEL]  = 0xFFD700
_fb_pal[_FB_WHT]  = 0xFFFFFF
_fb_pal[_FB_BLK]  = 0x000000
_fb_pal[_FB_CYN]  = 0x00FFCC

_fb_bmp = displayio.Bitmap(MATRIX_WIDTH, MATRIX_HEIGHT, 8)
_fb_tg  = displayio.TileGrid(_fb_bmp, pixel_shader=_fb_pal)
_fb_grp = displayio.Group()
_fb_grp.append(_fb_tg)
_fb_lbl = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF)
_fb_grp.append(_fb_lbl)

_FB_GY   = 27     # ground top y
_FB_BX   = 10     # bird fixed x
_FB_BW   = 4      # bird width
_FB_BH   = 3      # bird height
_FB_PW   = 5      # pipe width
_FB_GAP  = 9      # gap between top/bottom pipe
_FB_GRAV = 0.32
_FB_FLAP = -2.7
_FB_SPD0 = 1.0

_FB_DIGITS = [
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


def show_startup_message():
    """Display 'Waiting...' message on matrix."""
    text_group = displayio.Group()

    # Create text labels
    text1 = label.Label(
        terminalio.FONT,
        text="WAITING",
        color=0x00FF00,  # Green
        x=8,
        y=12
    )
    text2 = label.Label(
        terminalio.FONT,
        text="FOR USB",
        color=0x00FF00,
        x=8,
        y=22
    )

    text_group.append(text1)
    text_group.append(text2)
    display.root_group = text_group


def show_kitten():
    """Display kitten image for self-check."""
    print("Self-check: Displaying kitten...")

    # Load the kitten image
    kitten_bitmap, kitten_palette = load("/kitten.bmp")

    # Create a TileGrid to display the image
    kitten_grid = displayio.TileGrid(kitten_bitmap, pixel_shader=kitten_palette)
    kitten_group = displayio.Group()
    kitten_group.append(kitten_grid)

    # Show the image
    display.root_group = kitten_group
    time.sleep(5)
    print("Self-check complete!")


def show_dog():
    """Display dog image."""
    dog_bitmap, dog_palette = load("/dog.bmp")
    dog_grid = displayio.TileGrid(dog_bitmap, pixel_shader=dog_palette)
    dog_group = displayio.Group()
    dog_group.append(dog_grid)
    display.root_group = dog_group
    time.sleep(5)


def trigger_snap():
    """Signal the host to save a snapshot.
    Prints SNAP to the USB console port; the host can monitor that port
    (usb_cdc.console / the first CDC serial device) and act on it.
    """
    print("SNAP")


def show_bird_hint():
    """Display 'push DOWN for silly bird game' hint."""
    lines = [
        ("PUSH DOWN", 0xFFFF00),
        ("FOR SILLY", 0x00FFCC),
        ("BIRD GAME", 0xFF8800),
    ]
    hint_group = displayio.Group()
    for i, (text, color) in enumerate(lines):
        x = (MATRIX_WIDTH - len(text) * 6) // 2
        hint_group.append(label.Label(terminalio.FONT, text=text, color=color, x=x, y=7 + i * 10))
    display.root_group = hint_group
    time.sleep(5)


def _fb_box(x, y, w, h, c):
    x1 = max(0, x);             y1 = max(0, y)
    x2 = min(MATRIX_WIDTH, x+w); y2 = min(MATRIX_HEIGHT, y+h)
    if x2 > x1 and y2 > y1:
        bitmaptools.fill_region(_fb_bmp, x1, y1, x2, y2, c)

def _fb_dot(x, y, c):
    if 0 <= x < MATRIX_WIDTH and 0 <= y < MATRIX_HEIGHT:
        _fb_bmp[x, y] = c

def _fb_draw_score(n):
    x = 1
    for ch in str(n):
        rows = _FB_DIGITS[int(ch)]
        for r, bits in enumerate(rows):
            for b in range(3):
                if bits & (1 << (2 - b)):
                    _fb_dot(x + b, 1 + r, _FB_CYN)
        x += 4

def _fb_draw_bird(by, bird_v=0.0):
    by = int(by)
    _fb_box(_FB_BX, by, _FB_BW, _FB_BH, _FB_YEL)
    _fb_dot(_FB_BX + 3, by,     _FB_WHT)
    _fb_dot(_FB_BX + 3, by + 1, _FB_BLK)
    # Wing pixel animates with velocity: up when climbing, down when falling
    if bird_v < -1.0:
        _fb_dot(_FB_BX + 1, by - 1, _FB_YEL)              # wing up
    elif bird_v > 0.5 and by + _FB_BH < _FB_GY:
        _fb_dot(_FB_BX + 1, by + _FB_BH, _FB_YEL)         # wing down

def _fb_draw_pipe(px, gy):
    px = int(px)
    if gy > 2:
        _fb_box(px, 0, _FB_PW, gy - 2, _FB_PIPE)
    if gy > 0:
        _fb_box(px - 1, gy - 2, _FB_PW + 2, 2, _FB_CAP)
    bot = gy + _FB_GAP
    if bot < _FB_GY:
        _fb_box(px - 1, bot, _FB_PW + 2, 2, _FB_CAP)
    if bot + 2 < _FB_GY:
        _fb_box(px, bot + 2, _FB_PW, _FB_GY - bot - 2, _FB_PIPE)

def _fb_draw_scene():
    _fb_box(0, 0, MATRIX_WIDTH, _FB_GY, _FB_SKY)
    _fb_box(0, _FB_GY, MATRIX_WIDTH, MATRIX_HEIGHT - _FB_GY, _FB_GND)

def _fb_collides(by, pipes):
    by = int(by)
    if by < 0 or by + _FB_BH > _FB_GY:
        return True
    for p in pipes:
        px = int(p[0])
        gy = p[1]
        if _FB_BX + _FB_BW > px and _FB_BX < px + _FB_PW:
            if by < gy or by + _FB_BH > gy + _FB_GAP:
                return True
    return False

def run_flappy_bird():
    """Run Flappy Bird. Returns after game over so the caller can restore the display."""
    print("Launching Flappy Bird...")
    display.root_group = _fb_grp

    # Title screen
    _fb_draw_scene()
    _fb_draw_pipe(44, 8)
    _fb_draw_pipe(30, 14)
    _fb_draw_bird(_FB_GY // 2 - 1)
    _fb_lbl.text = "FLAP!"
    _fb_lbl.color = 0xFFD700
    _fb_lbl.x, _fb_lbl.y = 17, 8
    _fb_lbl.hidden = False
    display.refresh()

    # Drain any buttons still held from the DOWN press that launched us
    while not button_up.value or not button_down.value or not ext_button.value:
        button_up.update(); button_down.update(); ext_button.update()
        time.sleep(0.01)

    # Title screen: UP or ext=play, DOWN=exit
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if button_down.fell:
            return                          # back to camera / waiting screen
        if button_up.fell or ext_button.fell:
            break                           # start game
        time.sleep(0.02)

    # Game loop
    _fb_lbl.hidden = True
    bird_y = float(_FB_GY // 2)
    bird_v = 0.0
    pipes  = []          # [x, gap_y, scored]
    score  = 0
    spd    = _FB_SPD0
    dist   = 32.0

    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if not button_up.value and not button_down.value:
            return                          # both built-in buttons held = quit
        if button_up.fell or button_down.fell or ext_button.fell:
            bird_v = _FB_FLAP

        bird_v += _FB_GRAV
        bird_y += bird_v

        dist -= spd
        if dist <= 0:
            dist = 32.0
            gy = random.randint(4, _FB_GY - _FB_GAP - 4)
            pipes.append([float(MATRIX_WIDTH), gy, False])

        kept = []
        for p in pipes:
            p[0] -= spd
            if not p[2] and p[0] + _FB_PW < _FB_BX:
                p[2] = True
                score += 1
                spd = _FB_SPD0 + score * 0.08
            if p[0] > -_FB_PW - 2:
                kept.append(p)
        pipes = kept

        _fb_draw_scene()
        for p in pipes:
            _fb_draw_pipe(p[0], p[1])
        _fb_draw_bird(bird_y, bird_v)
        _fb_draw_score(score)
        display.refresh()

        if _fb_collides(bird_y, pipes):
            break

        time.sleep(0.05)   # ~20 FPS

    # Game over: flash score then return
    _fb_lbl.text = "DEAD"
    _fb_lbl.color = 0xFF2200
    _fb_lbl.x, _fb_lbl.y = 20, 16
    _fb_lbl.hidden = False
    for _ in range(3):
        _fb_draw_scene()
        _fb_draw_score(score)
        display.refresh()
        time.sleep(0.22)
        bitmaptools.fill_region(_fb_bmp, 0, 0, MATRIX_WIDTH, MATRIX_HEIGHT, _FB_BLK)
        display.refresh()
        time.sleep(0.13)
    _fb_draw_scene()
    _fb_draw_score(score)
    display.refresh()
    time.sleep(1.5)
    print(f"Flappy Bird — score: {score}")


def receive_frame(serial):
    """Receive the latest complete frame from the serial buffer.
    Clears old data to reduce latency and ensures synchronization.
    """
    # Check if serial port is available
    if serial is None:
        return None

    # Start reading as soon as we have at least the header
    # This prevents sender timeout by draining the buffer eagerly
    if serial.in_waiting < len(FRAME_HEADER):
        return None

    # Read everything available to find the most recent frame
    all_data = serial.read(serial.in_waiting)
    
    # Search for the header from the end (freshest frame)
    header_idx = all_data.rfind(FRAME_HEADER)
    
    if header_idx == -1:
        return None
        
    start_payload = header_idx + len(FRAME_HEADER)
    
    if len(all_data) >= start_payload + FRAME_SIZE:
        # Full frame is already in our buffer
        return all_data[start_payload : start_payload + FRAME_SIZE]
    else:
        # We found a header but the frame data is still arriving
        payload = bytearray(all_data[start_payload:])
        remaining = FRAME_SIZE - len(payload)
        
        # Wait a short time for the rest
        timeout = 0.1
        start_t = time.monotonic()
        while remaining > 0:
            if time.monotonic() - start_t > timeout:
                print("Sync timeout")
                return None
            if serial.in_waiting > 0:
                chunk = serial.read(min(serial.in_waiting, remaining))
                payload.extend(chunk)
                remaining -= len(chunk)
        return payload

def display_frame(frame_bytes):
    """Update bitmap with RGB565 frame data as efficiently as possible.
    
    Uses bitmaptools for C-level memory copy.
    Verified on M4 hardware to support ~147 FPS throughput.
    """
    # Create an array view of the bytes (treats them as 16-bit values)
    # The Matrix Portal M4 is little-endian, matching the sending format
    # Note: 'H' is unsigned short (2 bytes), matching RGB565
    pixel_array = array.array('H', frame_bytes)
    
    # Blit directly into the bitmap's memory
    bitmaptools.arrayblit(bitmap, pixel_array, x1=0, y1=0, x2=MATRIX_WIDTH, y2=MATRIX_HEIGHT)


def main():
    """Main loop: receive and display frames."""
    print("Matrix Portal M4 USB Frame Receiver")
    print(f"Display: {MATRIX_WIDTH}x{MATRIX_HEIGHT}")
    print(f"Max FPS: {MAX_FPS}")
    print("Waiting for frames...")

    # Show startup message on matrix
    show_startup_message()

    serial = usb_cdc.data

    # Verify serial port is available
    if serial is None:
        print("ERROR: usb_cdc.data is not available!")
        print("Check that boot.py enables data port")
        while True:
            time.sleep(1)

    print(f"USB data port ready: {serial}")
    print(f"Timeout: {serial.timeout}")

    frame_count = 0
    last_display_time = 0
    min_frame_time = 1.0 / MAX_FPS
    receiving_frames = False
    up_cycle = 0   # cycles: 0=kitten  1=dog  2=bird-game hint

    while True:
        button_up.update(); button_down.update(); ext_button.update()

        # UP button cycles: kitten → dog → "push DOWN for bird game" hint
        if button_up.fell:
            if up_cycle == 0:
                show_kitten()
            elif up_cycle == 1:
                show_dog()
            else:
                show_bird_hint()
            up_cycle = (up_cycle + 1) % 3
            if receiving_frames:
                display.root_group = group
            else:
                show_startup_message()
            # Resync debouncer after the blocking show_* call (may have been
            # seconds with no update(); drain any held state before continuing)
            while not button_up.value:
                button_up.update()
                time.sleep(0.01)

        # External snap button — sends SNAP to the USB console for the host to act on
        if ext_button.fell:
            trigger_snap()

        # DOWN button launches Flappy Bird
        if button_down.fell:
            run_flappy_bird()
            if receiving_frames:
                display.root_group = group
            else:
                show_startup_message()
            while not button_down.value:
                button_down.update()
                time.sleep(0.01)

        current_time = time.monotonic()

        # Check if enough time has passed for next frame
        if current_time - last_display_time < min_frame_time:
            time.sleep(0.01)
            continue

        # Try to receive a frame
        frame_data = receive_frame(serial)

        if frame_data:
            # Switch to bitmap display on first frame
            if not receiving_frames:
                display.root_group = group
                receiving_frames = True
                print("Receiving frames!")

            # Display the frame
            display_frame(frame_data)

            frame_count += 1
            last_display_time = current_time

            if frame_count % 10 == 0:
                print(f"Frames displayed: {frame_count}")
        else:
            # No data available, small delay
            time.sleep(0.01)


if __name__ == "__main__":
    main()
