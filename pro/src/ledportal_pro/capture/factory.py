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
    from ..exceptions import CameraNotFoundError

    system = platform.system()

    # On Linux (Raspberry Pi), try Pi Camera first if preferred
    if system == "Linux" and config.prefer_picamera:
        try:
            from .picamera import PiCamera

            camera = PiCamera(config)
            # Actually try to open it to see if picamera2 is installed
            camera.open()
            camera.close()  # Close it so caller can open it properly
            return camera
        except (ImportError, CameraNotFoundError) as e:
            # Print helpful message based on error type
            if isinstance(e, CameraNotFoundError):
                # picamera2 library not installed
                print("picamera2 not available in this environment.")
                print("On Raspberry Pi OS, install with: sudo apt install python3-picamera2")
                print("Then recreate venv with: uv venv --system-site-packages && uv sync")
            else:
                # Import error for our .picamera module (shouldn't happen)
                print("Pi Camera module not available.")
            print("Falling back to OpenCV...\n")

    # Default to OpenCV for all platforms
    return OpenCVCamera(config)


def list_available_cameras() -> list[dict[str, str | int | float]]:
    """List available cameras on the system with detailed information.

    On Linux, tries picamera2 first. If a Pi Camera is found, skips the OpenCV
    V4L2 scan (which produces noisy warnings on Raspberry Pi).

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

    # On Linux, try picamera2 first (before noisy OpenCV V4L2 scan)
    if platform.system() == "Linux":
        try:
            from picamera2 import Picamera2

            try:
                picam = Picamera2()
                camera_props = picam.camera_properties
                sensor_modes = picam.sensor_modes

                if sensor_modes:
                    mode = sensor_modes[0]
                    width = mode["size"][0]
                    height = mode["size"][1]
                    resolution = f"{width}x{height}"
                else:
                    resolution = "unknown"
                    width = 0
                    height = 0

                cameras.append(
                    {
                        "index": 0,
                        "type": "picamera",
                        "backend": "libcamera",
                        "resolution": resolution,
                        "width": width,
                        "height": height,
                        "fps": "varies",
                        "name": camera_props.get("Model", "Pi Camera"),
                    }
                )
                picam.close()
                # Pi Camera found — skip OpenCV V4L2 scan (it produces noisy
                # warnings and can't use the Pi Camera via libcamera anyway)
                return cameras
            except Exception:
                pass
        except ImportError:
            pass

    # OpenCV scan (macOS/Windows, or Linux without picamera2)
    import cv2

    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            backend = cap.getBackendName()

            cameras.append(
                {
                    "index": i,
                    "type": "opencv",
                    "backend": backend,
                    "resolution": f"{width}x{height}",
                    "width": width,
                    "height": height,
                    "fps": fps if fps > 0 else "unknown",
                    "name": f"Camera {i}",
                }
            )
            cap.release()

    return cameras
