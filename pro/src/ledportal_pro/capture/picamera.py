"""Pi Camera implementation for Raspberry Pi."""

from typing import TYPE_CHECKING, Any

import cv2
import numpy as np
from numpy.typing import NDArray

from ..exceptions import CameraCaptureFailed, CameraNotFoundError
from .base import CameraBase

if TYPE_CHECKING:
    from ..config import CameraConfig


class PiCamera(CameraBase):
    """Camera implementation using picamera2 for Raspberry Pi."""

    def __init__(self, config: CameraConfig) -> None:
        """Initialize Pi Camera.

        Args:
            config: Camera configuration settings.
        """
        super().__init__(config)
        self._picam: Any = None  # Picamera2 instance

    def open(self) -> None:
        """Open Pi Camera.

        Raises:
            CameraNotFoundError: If Pi Camera is not available.
        """
        try:
            from picamera2 import Picamera2
        except ImportError as e:
            raise CameraNotFoundError(
                "picamera2 is not installed. Install with: pip install picamera2"
            ) from e

        try:
            self._picam = Picamera2()
            config = self._picam.create_preview_configuration(
                main={"size": (self._config.width, self._config.height)}
            )
            self._picam.configure(config)
            self._picam.start()
            self._is_open = True
        except Exception as e:
            raise CameraNotFoundError(f"Failed to initialize Pi Camera: {e}") from e

    def close(self) -> None:
        """Stop and close Pi Camera."""
        if self._picam is not None:
            try:
                self._picam.stop()
                self._picam.close()
            except Exception:
                pass  # Ignore errors during cleanup
            self._picam = None
        self._is_open = False

    def capture(self) -> NDArray[np.uint8]:
        """Capture a frame from Pi Camera.

        Returns:
            BGR image as numpy array.

        Raises:
            CameraCaptureFailed: If frame capture fails.
        """
        if self._picam is None:
            raise CameraCaptureFailed("Pi Camera is not open")

        try:
            # Pi Camera returns RGB, convert to BGR for OpenCV compatibility
            frame = self._picam.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
        except Exception as e:
            raise CameraCaptureFailed(f"Failed to capture frame: {e}") from e

    def get_camera_type(self) -> str:
        """Get camera type identifier."""
        return "picamera"
