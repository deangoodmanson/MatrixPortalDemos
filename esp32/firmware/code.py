"""
Waveshare ESP32-C6 LCD 1.47 — Bootstrap
v1: Silly Bird only, landscape, single button (board.BUTTON).

board.DISPLAY is auto-initialized by CircuitPython for this board (ST7789
BusDisplay) — no manual display driver setup needed, unlike the Matrix
Portal's manual rgbmatrix.RGBMatrix() construction.
"""
import board
import digitalio
from adafruit_debouncer import Debouncer

import silly_bird

display = board.DISPLAY
display.rotation = 90  # 320x172 landscape (native panel is 172x320 portrait)
# board.DISPLAY defaults to auto_refresh=True (background thread refreshes on a
# timer). silly_bird.py also calls display.refresh() manually every frame — with
# auto_refresh left on, the two race over the SPI bus: frames tear/flicker, and
# each manual refresh() blocks waiting its turn behind the auto-refresh thread,
# stalling the whole game loop (including the button poll that follows it).
display.auto_refresh = False

_pin_button = digitalio.DigitalInOut(board.BUTTON)
_pin_button.switch_to_input(pull=digitalio.Pull.UP)
button = Debouncer(_pin_button)

silly_bird.run(display, button)
