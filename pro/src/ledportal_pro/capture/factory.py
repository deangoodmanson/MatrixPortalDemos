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


def list_available_cameras() -> list[dict[str, str | int | float]]:
    """List available cameras on the system with detailed information.

    Returns:
        List of dictionaries with camera information including:
        - index: Camera index
        - type: Camera type (opencv/picamera)
        - backend: Backend name
        - resolution: Current resolution (width x height)
        - fps: Frames per second capability
        - name: Camera device name (if available)
    """
    cameras: list[dict[str, str | int | float]] = []
    import cv2

    # Check first 10 camera indices (increased from 5)
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            backend = cap.getBackendName()

            # Try to get camera name/description
            # This is backend-dependent and may not always work
            camera_name = f"Camera {i}"

            cameras.append(
                {
                    "index": i,
                    "type": "opencv",
                    "backend": backend,
                    "resolution": f"{width}x{height}",
                    "width": width,
                    "height": height,
                    "fps": fps if fps > 0 else "unknown",
                    "name": camera_name,
                }
            )
            cap.release()

    # Check for Pi Camera on Linux
    if platform.system() == "Linux":
        try:
            from picamera2 import Picamera2

            try:
                picam = Picamera2()
                # Get Pi Camera properties
                camera_props = picam.camera_properties
                sensor_modes = picam.sensor_modes

                # Get default resolution from first sensor mode
                if sensor_modes:
                    mode = sensor_modes[0]
                    width = mode['size'][0]
                    height = mode['size'][1]
                    resolution = f"{width}x{height}"
                else:
                    resolution = "unknown"
                    width = 0
                    height = 0

                cameras.append({
                    "index": 0,
                    "type": "picamera",
                    "backend": "libcamera",
                    "resolution": resolution,
                    "width": width,
                    "height": height,
                    "fps": "varies",
                    "name": camera_props.get('Model', 'Pi Camera'),
                })
                picam.close()
            except Exception:
                pass
        except ImportError:
            pass

    return cameras
