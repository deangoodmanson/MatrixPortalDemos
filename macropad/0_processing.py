# SPDX-License-Identifier: MIT
"""LED Portal - Processing Modes (page 0)"""

from adafruit_hid.keycode import Keycode

CYAN   = 0x004444
DIM    = 0x111111
RED    = 0x440000
ORANGE = 0x442200

app = {
    'name': 'Processing',
    'macros': [
        # Row 0 — processing modes
        (CYAN,   'CROP',   [Keycode.C]),
        (CYAN,   'STRCH',  [Keycode.S]),
        (CYAN,   'FIT',    [Keycode.F]),
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
