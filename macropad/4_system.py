# SPDX-License-Identifier: MIT
"""LED Portal - System (page 4)"""

from adafruit_hid.keycode import Keycode

ORANGE = 0x442200
TEAL   = 0x004422
DIM    = 0x111111
RED    = 0x440000

app = {
    'name': 'System',
    'macros': [
        # Row 0 — debug / preview / demo
        (TEAL,   'DEBUG',  [Keycode.D]),
        (TEAL,   'PREVW',  [Keycode.W]),
        (TEAL,   'DEMO',   [Keycode.X]),
        # Row 1 — help / reset / manual demo
        (ORANGE, 'HELP',   [Keycode.H]),
        (ORANGE, 'RESET',  [Keycode.R]),
        (TEAL,   'MNDMO',  [Keycode.LEFT_SHIFT, Keycode.X]),
        # Row 2 — demo navigation
        (TEAL,   '< PRV',  [Keycode.COMMA]),
        (TEAL,   'NXT >',  [Keycode.PERIOD]),
        (0,      '',       []),
        # Row 3 — repeaters (RESET duplicated intentionally — muscle memory)
        (DIM,    'RESET',  [Keycode.R]),
        (ORANGE, 'TX',     [Keycode.T]),
        (RED,    'QUIT',   [Keycode.Q]),
        # Encoder click — snapshot
        (0,      '',       [Keycode.SPACE]),
    ]
}
