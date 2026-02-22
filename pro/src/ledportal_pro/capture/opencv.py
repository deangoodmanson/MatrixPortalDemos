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
        # Try the requested index first
        self._cap = cv2.VideoCapture(self._config.index)

        if not self._cap.isOpened():
            # If the requested index fails and it's index 0, try other indices
            if self._config.index == 0:
                print("Camera index 0 failed, trying other indices...")
                for i in range(1, 5):
                    self._cap = cv2.VideoCapture(i)
                    if self._cap.isOpened():
                        print(f"Found camera at index {i}")
                        self._config.index = i  # Update config to reflect actual index
                        break
                    self._cap.release()

            # If still not opened, raise error with helpful message
            if not self._cap.isOpened():
                import platform

                error_msg = f"Failed to open camera at index {self._config.index}"
                if platform.system() == "Linux":
                    error_msg += (
                        "\n\nTroubleshooting on Raspberry Pi:"
                        "\n  - Check camera is connected: lsusb (for USB) or vcgencmd get_camera (for Pi Camera)"
                        "\n  - Try installing system OpenCV: sudo apt install python3-opencv"
                        "\n  - Check camera isn't in use: fuser /dev/video0"
                        "\n  - List available cameras: v4l2-ctl --list-devices"
                    )
                raise CameraNotFoundError(error_msg)

        # Only set resolution if explicitly configured (non-zero values)
        # Otherwise, use camera's native resolution
        if self._config.width > 0 and self._config.height > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.height)

            # Verify camera can actually capture frames with this resolution
            ret, test_frame = self._cap.read()
            if not ret or test_frame is None:
                print(f"Warning: Camera doesn't support {self._config.width}x{self._config.height}")

                # Reset to use native resolution
                self._cap.release()
                self._cap = cv2.VideoCapture(self._config.index)

                if not self._cap.isOpened():
                    raise CameraNotFoundError(
                        f"Failed to reopen camera at index {self._config.index}"
                    )

                ret, test_frame = self._cap.read()
                if not ret or test_frame is None:
                    raise CameraNotFoundError(
                        f"Camera at index {self._config.index} cannot capture frames"
                    )

                native_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                native_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"Using native resolution: {native_width}x{native_height}")
        else:
            # Use camera's default resolution
            ret, test_frame = self._cap.read()
            if not ret or test_frame is None:
                raise CameraNotFoundError(
                    f"Camera at index {self._config.index} cannot capture frames"
                )

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

        return np.asarray(frame, dtype=np.uint8)

    def get_camera_type(self) -> str:
        """Get camera type identifier."""
        return "opencv"

    def get_camera_info(self) -> dict[str, str | int | float]:
        """Get detailed information about the camera.

        Returns:
            Dictionary with camera information.
        """
        if self._cap is None or not self._cap.isOpened():
            return {
                "type": "opencv",
                "index": self._config.index,
                "status": "not_opened",
            }

        # Get actual camera properties
        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        backend = self._cap.getBackendName()
        fourcc = int(self._cap.get(cv2.CAP_PROP_FOURCC))

        # Decode FOURCC to readable format
        fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

        return {
            "type": "opencv",
            "index": self._config.index,
            "backend": backend,
            "resolution": f"{width}x{height}",
            "width": width,
            "height": height,
            "fps": fps if fps > 0 else "unknown",
            "format": fourcc_str if fourcc > 0 else "unknown",
            "requested_resolution": f"{self._config.width}x{self._config.height}",
        }
