import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import sys
import os

# Mock dependencies for camera_feed
sys.modules['cv2'] = MagicMock()
sys.modules['serial'] = MagicMock()
sys.modules['serial.tools.list_ports'] = MagicMock()

# Add mac to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../mac')))
import camera_feed

class TestSender(unittest.TestCase):
    def test_send_frame_includes_header(self):
        """Verify that send_frame_usb writes the header before the frame data."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        
        frame_bytes = b'\x01\x02\x03\x04'
        camera_feed.send_frame_usb(mock_serial, frame_bytes)
        
        # Check calls to write
        # First call should be the header
        self.assertEqual(mock_serial.write.call_args_list[0][0][0], camera_feed.FRAME_HEADER)
        # Second call should be the frame data
        self.assertEqual(mock_serial.write.call_args_list[1][0][0], frame_bytes)

if __name__ == '__main__':
    unittest.main()
