# SPDX-License-Identifier: MIT
"""LED Portal - Actions (page 2)"""

from adafruit_hid.keycode import Keycode

GREEN  = 0x004400
DIM    = 0x111111
RED    = 0x440000
ORANGE = 0x442200

app = {
    'name': 'Actions',
    'macros': [
        # Row 0 — actions
        (GREEN,  'SNAP',   [Keycode.SPACE]),
        (GREEN,  'AVTR',   [Keycode.V]),
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
