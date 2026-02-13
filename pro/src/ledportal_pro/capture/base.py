"""Abstract base class for camera capture."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from ..config import CameraConfig


class CameraBase(ABC):
    """Abstract base class for camera implementations."""

    def __init__(self, config: CameraConfig) -> None:
        """Initialize camera with configuration.

        Args:
            config: Camera configuration settings.
        """
        self._config = config
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """Check if camera is currently open."""
        return self._is_open

    @property
    def config(self) -> CameraConfig:
        """Get camera configuration."""
        return self._config

    @abstractmethod
    def open(self) -> None:
        """Open and initialize the camera.

        Raises:
            CameraNotFoundError: If camera cannot be found.
            CameraError: If camera fails to initialize.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the camera and release resources."""
        pass

    @abstractmethod
    def capture(self) -> NDArray[np.uint8]:
        """Capture a single frame from the camera.

        Returns:
            BGR image as numpy array with shape (height, width, 3).

        Raises:
            CameraCaptureFailed: If frame capture fails.
        """
        pass

    @abstractmethod
    def get_camera_type(self) -> str:
        """Get the type/name of this camera implementation.

        Returns:
            String identifier for the camera type.
        """
        pass

    @abstractmethod
    def get_camera_info(self) -> dict[str, str | int | float]:
        """Get detailed information about the camera.

        Returns:
            Dictionary with camera information including resolution, fps, backend, etc.
        """
        pass

    def __enter__(self) -> CameraBase:
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        """Context manager exit."""
        self.close()
