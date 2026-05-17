"""
Boot configuration for Matrix Portal M4.
Enables USB CDC data port for receiving frame data.
"""

import usb_cdc

usb_cdc.enable(console=True, data=True)
