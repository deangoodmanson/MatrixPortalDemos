# SPDX-License-Identifier: MIT
"""LED Portal - Orientation (page 3)"""

from adafruit_hid.keycode import Keycode

YELLOW = 0x444400
DIM    = 0x111111
RED    = 0x440000
ORANGE = 0x442200

app = {
    'name': 'Orientation',
    'macros': [
        # Row 0 — orientation
        (YELLOW, 'LNDSCP', [Keycode.L]),
        (YELLOW, 'PORTR',  [Keycode.P]),
        (0,      '',       []),
        # Row 1 — blank
        (0,      '',       []),
        (0,      '',       []),
        (0,      '',       []),
        # Row 2 — blank
        (0,      '',       []),
        (0,      '',       []),
        (0,      '',       []),
        # Row 3 — repeaters
        (DIM,    'RESET',  [Keycode.R]),
        (ORANGE, 'TX',     [Keycode.T]),
        (RED,    'QUIT',   [Keycode.Q]),
        # Encoder click — snapshot
        (0,      '',       [Keycode.SPACE]),
    ]
}
