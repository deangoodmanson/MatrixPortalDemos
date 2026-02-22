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
                "picamera2 is not installed. On Raspberry Pi OS, install with:\n"
                "  sudo apt install python3-picamera2\n"
                "Then recreate your venv with:\n"
                "  uv venv --system-site-packages && uv sync"
            ) from e

        try:
            self._picam = Picamera2()
            # If width/height are 0, let picamera2 choose its native resolution
            if self._config.width > 0 and self._config.height > 0:
                preview_config = self._picam.create_preview_configuration(
                    main={"size": (self._config.width, self._config.height)}
                )
            else:
                preview_config = self._picam.create_preview_configuration()
            self._picam.configure(preview_config)
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

    def get_camera_info(self) -> dict[str, str | int | float]:
        """Get detailed information about the Pi Camera.

        Returns:
            Dictionary with camera information.
        """
        if self._picam is None:
            return {
                "type": "picamera",
                "status": "not_opened",
            }

        # Get camera properties
        camera_props = self._picam.camera_properties
        config = self._picam.camera_configuration()

        # Get current resolution from configuration
        main_stream = config.get("main", {})
        size = main_stream.get("size", (0, 0))
        fmt = main_stream.get("format", "unknown")

        return {
            "type": "picamera",
            "backend": "libcamera",
            "model": camera_props.get("Model", "Unknown"),
            "resolution": f"{size[0]}x{size[1]}",
            "width": size[0],
            "height": size[1],
            "format": str(fmt),
            "requested_resolution": f"{self._config.width}x{self._config.height}",
            "sensor_modes": len(self._picam.sensor_modes),
        }
