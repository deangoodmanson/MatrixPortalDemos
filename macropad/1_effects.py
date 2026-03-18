# SPDX-License-Identifier: MIT
"""LED Portal - Effects (page 1)"""

from adafruit_hid.keycode import Keycode

MAGENTA = 0x440044
PURPLE  = 0x220044
DIM     = 0x111111
RED     = 0x440000
ORANGE  = 0x442200

app = {
    'name': 'Effects',
    'macros': [
        # Row 0 — color/image effects
        (MAGENTA, 'B&W',   [Keycode.B]),
        (MAGENTA, 'MIRRR', [Keycode.M]),
        (MAGENTA, 'ZOOM',  [Keycode.Z]),
        # Row 1 — render algorithm + LED size
        (PURPLE,  'ALGO',  [Keycode.O]),
        (PURPLE,  'SZ+',   [Keycode.EQUALS]),   # = triggers LED_SIZE_INCREASE
        (PURPLE,  'SZ-',   [Keycode.MINUS]),    # - triggers LED_SIZE_DECREASE
        # Row 2 — blank
        (0,       '',      []),
        (0,       '',      []),
        (0,       '',      []),
        # Row 3 — repeaters
        (DIM,     'RESET', [Keycode.R]),
        (ORANGE,  'TX',    [Keycode.T]),
        (RED,     'QUIT',  [Keycode.Q]),
        # Encoder click — snapshot
        (0,       '',      [Keycode.SPACE]),
    ]
}
