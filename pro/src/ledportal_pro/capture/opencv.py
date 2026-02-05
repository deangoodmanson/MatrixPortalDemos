"""OpenCV camera implementation for macOS and USB cameras."""

from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

from ..exceptions import CameraCaptureFailed, CameraNotFoundError
from .base import CameraBase

if TYPE_CHECKING:
    from ..config import CameraConfig


class OpenCVCamera(CameraBase):
    """Camera implementation using OpenCV VideoCapture."""

    def __init__(self, config: CameraConfig) -> None:
        """Initialize OpenCV camera.

        Args:
            config: Camera configuration settings.
        """
        super().__init__(config)
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        """Open camera using OpenCV.

        Raises:
            CameraNotFoundError: If camera cannot be opened.
        """
        self._cap = cv2.VideoCapture(self._config.index)

        if not self._cap.isOpened():
            raise CameraNotFoundError(f"Failed to open camera at index {self._config.index}")

        # Set capture resolution
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.height)

        self._is_open = True

    def close(self) -> None:
        """Release the OpenCV camera."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_open = False

    def capture(self) -> NDArray[np.uint8]:
        """Capture a frame using OpenCV.

        Returns:
            BGR image as numpy array.

        Raises:
            CameraCaptureFailed: If frame capture fails.
        """
        if self._cap is None or not self._cap.isOpened():
            raise CameraCaptureFailed("Camera is not open")

        ret, frame = self._cap.read()
        if not ret or frame is None:
            raise CameraCaptureFailed("Failed to read frame from camera")

        return frame

    def get_camera_type(self) -> str:
        """Get camera type identifier."""
        return "opencv"
