"""Camera factory for creating camera instances."""

import platform
from typing import TYPE_CHECKING

from .base import CameraBase
from .opencv import OpenCVCamera

if TYPE_CHECKING:
    from ..config import CameraConfig


def create_camera(config: CameraConfig) -> CameraBase:
    """Create appropriate camera instance based on platform and configuration.

    On Raspberry Pi (Linux), tries picamera2 first if prefer_picamera is True.
    Falls back to OpenCV if Pi Camera is not available.
    On other platforms (macOS, Windows), uses OpenCV directly.

    Args:
        config: Camera configuration settings.

    Returns:
        CameraBase instance appropriate for the current platform.

    Raises:
        CameraNotFoundError: If no suitable camera can be created.
    """
    system = platform.system()

    # On Linux (Raspberry Pi), try Pi Camera first if preferred
    if system == "Linux" and config.prefer_picamera:
        try:
            from .picamera import PiCamera

            camera = PiCamera(config)
            return camera
        except ImportError:
            # picamera2 not installed, fall through to OpenCV
            pass

    # Default to OpenCV for all platforms
    return OpenCVCamera(config)


def list_available_cameras() -> list[dict[str, str | int]]:
    """List available cameras on the system.

    Returns:
        List of dictionaries with camera information.
    """
    cameras: list[dict[str, str | int]] = []
    import cv2

    # Check first 5 camera indices
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append(
                {
                    "index": i,
                    "type": "opencv",
                    "backend": cap.getBackendName(),
                }
            )
            cap.release()

    # Check for Pi Camera on Linux
    if platform.system() == "Linux":
        try:
            from picamera2 import Picamera2

            try:
                picam = Picamera2()
                cameras.append({"index": 0, "type": "picamera", "backend": "libcamera"})
                picam.close()
            except Exception:
                pass
        except ImportError:
            pass

    return cameras
