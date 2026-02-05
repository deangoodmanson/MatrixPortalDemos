"""
Boot configuration for Matrix Portal M4.
Enables USB CDC data port for receiving frame data.
"""

import usb_cdc

# Enable the data serial port (in addition to console)
usb_cdc.enable(console=True, data=True)
