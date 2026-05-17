"""
Matrix Portal M4 — Bootstrap
Reads MODE from settings.toml and runs the configured app(s).

  MODE = "silly_bird"    — game only
  MODE = "image_display" — camera feed only
  MODE = "both"          — camera feed + Silly Bird; DOWN switches between them
"""
import os
import time
import board
import displayio
import rgbmatrix
import framebufferio
import digitalio
from adafruit_debouncer import Debouncer

# ── Hardware (always needed) ──────────────────────────────────────────────
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=6,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE,
)
display = framebufferio.FramebufferDisplay(matrix)
display.brightness = float(os.getenv("BRIGHTNESS", "0.75"))

_pin_up = digitalio.DigitalInOut(board.BUTTON_UP)
_pin_up.switch_to_input(pull=digitalio.Pull.UP)
button_up = Debouncer(_pin_up)

_pin_dn = digitalio.DigitalInOut(board.BUTTON_DOWN)
_pin_dn.switch_to_input(pull=digitalio.Pull.UP)
button_down = Debouncer(_pin_dn)

# External snap / flap button
# ── Wiring ────────────────────────────────────────────────────────────────
#  One side of the momentary switch → white wire (A0) on the JST PH connector
#  Other side of the switch         → black wire (GND) on the JST PH connector
#
#  Leave the red wire (3.3V) unconnected.
#  The JST PH 3-pin connector is next to the 5V screw terminal on the board.
#  No external resistor needed; internal pull-up is enabled below.
# ─────────────────────────────────────────────────────────────────────────
_pin_ext = digitalio.DigitalInOut(board.A0)
_pin_ext.switch_to_input(pull=digitalio.Pull.UP)
ext_button = Debouncer(_pin_ext)

# ── Config ────────────────────────────────────────────────────────────────
MODE = os.getenv("MODE", "both")
print(f"Matrix Portal M4 — mode: {MODE}")

# ── Mode: silly_bird ──────────────────────────────────────────────────────
if MODE == "silly_bird":
    import silly_bird
    while True:
        silly_bird.run(display, button_up, button_down, ext_button)

# ── Mode: image_display ───────────────────────────────────────────────────
elif MODE == "image_display":
    import usb_cdc
    import image_display

    serial = usb_cdc.data
    if serial is None:
        print("ERROR: usb_cdc.data not available — check boot.py")
        while True:
            time.sleep(1)

    bitmap = displayio.Bitmap(64, 32, 65536)
    camera_group = displayio.Group()
    camera_group.append(displayio.TileGrid(
        bitmap,
        pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565),
    ))

    image_display.show_startup_message(display)

    frame_count       = 0
    last_display_time = 0
    min_frame_time    = 1.0 / 30
    receiving_frames  = False
    up_cycle          = 0   # 0=kitten  1=dog  2=bird hint (still useful as teaser)

    while True:
        button_up.update(); button_down.update(); ext_button.update()

        if button_up.fell:
            if up_cycle == 0:
                image_display.show_kitten(display)
            elif up_cycle == 1:
                image_display.show_dog(display)
            else:
                image_display.show_bird_hint(display)
            up_cycle = (up_cycle + 1) % 3
            if receiving_frames:
                display.root_group = camera_group
            else:
                image_display.show_startup_message(display)
            while not button_up.value:
                button_up.update()
                time.sleep(0.01)

        if ext_button.fell:
            image_display.trigger_snap()

        current_time = time.monotonic()
        if current_time - last_display_time < min_frame_time:
            time.sleep(0.01)
            continue

        frame_data = image_display.receive_frame(serial)
        if frame_data:
            if not receiving_frames:
                display.root_group = camera_group
                receiving_frames = True
                print("Receiving frames!")
            image_display.display_frame(bitmap, frame_data)
            frame_count += 1
            last_display_time = current_time
            if frame_count % 10 == 0:
                print(f"Frames displayed: {frame_count}")
        else:
            time.sleep(0.01)

# ── Mode: both ────────────────────────────────────────────────────────────
else:
    import usb_cdc
    import image_display
    import silly_bird

    serial = usb_cdc.data
    if serial is None:
        print("ERROR: usb_cdc.data not available — check boot.py")
        while True:
            time.sleep(1)

    bitmap = displayio.Bitmap(64, 32, 65536)
    camera_group = displayio.Group()
    camera_group.append(displayio.TileGrid(
        bitmap,
        pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565),
    ))

    image_display.show_startup_message(display)

    frame_count       = 0
    last_display_time = 0
    min_frame_time    = 1.0 / 30
    receiving_frames  = False
    up_cycle          = 0   # 0=kitten  1=dog  2=silly bird hint

    while True:
        button_up.update(); button_down.update(); ext_button.update()

        # UP cycles: kitten → dog → "push DOWN for silly bird" hint
        if button_up.fell:
            if up_cycle == 0:
                image_display.show_kitten(display)
            elif up_cycle == 1:
                image_display.show_dog(display)
            else:
                image_display.show_bird_hint(display)
            up_cycle = (up_cycle + 1) % 3
            if receiving_frames:
                display.root_group = camera_group
            else:
                image_display.show_startup_message(display)
            while not button_up.value:
                button_up.update()
                time.sleep(0.01)

        # EXT → snapshot
        if ext_button.fell:
            image_display.trigger_snap()

        # DOWN → switch to Silly Bird; returns here when player exits
        if button_down.fell:
            silly_bird.run(display, button_up, button_down, ext_button)
            if receiving_frames:
                display.root_group = camera_group
            else:
                image_display.show_startup_message(display)
            while not button_down.value:
                button_down.update()
                time.sleep(0.01)

        current_time = time.monotonic()
        if current_time - last_display_time < min_frame_time:
            time.sleep(0.01)
            continue

        frame_data = image_display.receive_frame(serial)
        if frame_data:
            if not receiving_frames:
                display.root_group = camera_group
                receiving_frames = True
                print("Receiving frames!")
            image_display.display_frame(bitmap, frame_data)
            frame_count += 1
            last_display_time = current_time
            if frame_count % 10 == 0:
                print(f"Frames displayed: {frame_count}")
        else:
            time.sleep(0.01)
