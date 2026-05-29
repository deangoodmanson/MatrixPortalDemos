"""
Matrix Portal M4 — Image Display
Camera feed reception and image/text display functions.
"""
import time
import displayio
import bitmaptools
import array
from adafruit_display_text import label
from adafruit_imageload import load
import terminalio

MATRIX_WIDTH  = 64
MATRIX_HEIGHT = 32
FRAME_SIZE    = MATRIX_WIDTH * MATRIX_HEIGHT * 2  # RGB565, 2 bytes/pixel
FRAME_HEADER  = b'IMG1'

# Kept at module level so the GC doesn't collect groups that are still displayed.
_current_group = None


def show_startup_message(display):
    """Show the idle hub screen: USB:MIRROR / UP:PHOTOS / DN:BIRD."""
    global _current_group
    rows = [
        ("MIRROR",     0x0066FF,  5),
        ("UP:PHOTOS",  0xADD8E6, 15),
        ("DN:BIRD",    0xFFD700, 25),
    ]
    grp = displayio.Group()
    for text, color, y in rows:
        x = max(0, (MATRIX_WIDTH - len(text) * 6) // 2)
        grp.append(label.Label(terminalio.FONT, text=text, color=color, x=x, y=y))
    _current_group = grp
    display.root_group = grp


def _wait_for_button(button_up, button_down, ext_button):
    """Poll until a button is pressed; return 'up', 'down', or 'ext'."""
    while True:
        button_up.update(); button_down.update(); ext_button.update()
        if ext_button.fell:
            return "ext"
        if button_up.fell:
            return "up"
        if button_down.fell:
            return "down"
        time.sleep(0.02)


def _show_photo(display, path):
    """Load and display a BMP image."""
    global _current_group
    bmp, pal = load(path)
    grp = displayio.Group()
    grp.append(displayio.TileGrid(bmp, pixel_shader=pal))
    _current_group = grp
    display.root_group = grp


def run_photo_mode(display, button_up, button_down, ext_button):
    """Sticky photo slideshow: UP cycles kitten→dog→bird hint, EXT returns to hub.

    Stays in photo mode until the player presses EXT.  Each UP press advances
    to the next photo; DOWN is ignored inside photo mode.
    """
    # Wait for the UP press that entered this mode to be fully released
    while not button_up.value:
        button_up.update()
        time.sleep(0.01)

    photos = ["/kitten.bmp", "/dog.bmp"]
    idx = 0

    while True:
        if idx < len(photos):
            _show_photo(display, photos[idx])
        else:
            _show_bird_hint(display)

        pressed = _wait_for_button(button_up, button_down, ext_button)
        if pressed == "ext":
            return          # back to STARTUP_SCREEN
        if pressed == "up":
            idx = (idx + 1) % (len(photos) + 1)
        # DOWN is ignored in photo mode


def show_kitten(display):
    """Display kitten.bmp — used for the boot self-check."""
    print("Self-check: Displaying kitten...")
    _show_photo(display, "/kitten.bmp")
    time.sleep(5)
    print("Self-check complete!")


def _show_bird_hint(display):
    """Show the 'PUSH DOWN FOR SILLY BIRD GAME' teaser screen."""
    global _current_group
    lines = [
        ("PUSH DOWN", 0xFFFF00),
        ("FOR SILLY", 0x00FFCC),
        ("BIRD GAME", 0xFF8800),
    ]
    grp = displayio.Group()
    for i, (text, color) in enumerate(lines):
        x = (MATRIX_WIDTH - len(text) * 6) // 2
        grp.append(label.Label(terminalio.FONT, text=text, color=color, x=x, y=7 + i * 10))
    _current_group = grp
    display.root_group = grp


def trigger_snap():
    """Send SNAP to the USB console so the host can save a snapshot."""
    print("SNAP")


def receive_frame(serial):
    """Return the most recent complete RGB565 frame from the serial buffer, or None."""
    if serial is None or serial.in_waiting < len(FRAME_HEADER):
        return None
    all_data = serial.read(serial.in_waiting)
    header_idx = all_data.rfind(FRAME_HEADER)
    if header_idx == -1:
        return None
    start = header_idx + len(FRAME_HEADER)
    if len(all_data) >= start + FRAME_SIZE:
        return all_data[start : start + FRAME_SIZE]
    payload   = bytearray(all_data[start:])
    remaining = FRAME_SIZE - len(payload)
    deadline  = time.monotonic() + 0.1
    while remaining > 0:
        if time.monotonic() > deadline:
            print("Sync timeout")
            return None
        if serial.in_waiting > 0:
            chunk = serial.read(min(serial.in_waiting, remaining))
            payload.extend(chunk)
            remaining -= len(chunk)
    return payload


def display_frame(bitmap, frame_bytes):
    """Blit an RGB565 frame into the bitmap using C-level arrayblit."""
    bitmaptools.arrayblit(
        bitmap, array.array('H', frame_bytes),
        x1=0, y1=0, x2=MATRIX_WIDTH, y2=MATRIX_HEIGHT,
    )
