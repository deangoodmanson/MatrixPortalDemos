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


def show_startup_message(display):
    """Mode/button guide shown while waiting for USB camera connection.

    3-row layout, each row centred:
      USB:CAM   — camera feed starts automatically when PC connects
      UP:PHOTOS — UP button cycles photo slideshow
      DN:BIRD   — DOWN button launches Silly Bird game
    """
    rows = [
        ("USB:CAM",   0x0066FF,  5),
        ("UP:PHOTOS", 0xFFD700, 15),
        ("DN:BIRD",   0x00FFCC, 25),
    ]
    grp = displayio.Group()
    for text, color, y in rows:
        x = max(0, (MATRIX_WIDTH - len(text) * 6) // 2)
        grp.append(label.Label(terminalio.FONT, text=text, color=color, x=x, y=y))
    display.root_group = grp


def show_kitten(display):
    print("Self-check: Displaying kitten...")
    bmp, pal = load("/kitten.bmp")
    grp = displayio.Group()
    grp.append(displayio.TileGrid(bmp, pixel_shader=pal))
    display.root_group = grp
    time.sleep(5)
    print("Self-check complete!")


def show_dog(display):
    bmp, pal = load("/dog.bmp")
    grp = displayio.Group()
    grp.append(displayio.TileGrid(bmp, pixel_shader=pal))
    display.root_group = grp
    time.sleep(5)


def show_bird_hint(display):
    lines = [
        ("PUSH DOWN", 0xFFFF00),
        ("FOR SILLY", 0x00FFCC),
        ("BIRD GAME", 0xFF8800),
    ]
    grp = displayio.Group()
    for i, (text, color) in enumerate(lines):
        x = (MATRIX_WIDTH - len(text) * 6) // 2
        grp.append(label.Label(terminalio.FONT, text=text, color=color, x=x, y=7 + i * 10))
    display.root_group = grp
    time.sleep(5)


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
