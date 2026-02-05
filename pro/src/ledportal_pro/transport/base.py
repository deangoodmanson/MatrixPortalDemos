"""Abstract base class for transport implementations."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import TransportConfig


class TransportBase(ABC):
    """Abstract base class for transport implementations."""

    def __init__(self, config: TransportConfig) -> None:
        """Initialize transport with configuration.

        Args:
            config: Transport configuration settings.
        """
        self._config = config
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Check if transport is currently connected."""
        return self._is_connected

    @property
    def config(self) -> TransportConfig:
        """Get transport configuration."""
        return self._config

    @property
    def port(self) -> str | None:
        """Get the connected port/device path.

        Returns:
            Port path if connected, None otherwise.
        """
        return None

    @abstractmethod
    def connect(self, port: str | None = None) -> None:
        """Establish connection to the device.

        Args:
            port: Optional port/device path. If None, auto-detect.

        Raises:
            DeviceNotFoundError: If device cannot be found.
            ConnectionError: If connection fails.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection and release resources."""
        pass

    @abstractmethod
    def send_frame(self, frame_data: bytes) -> int:
        """Send frame data to the device.

        Args:
            frame_data: Raw frame bytes to send.

        Returns:
            Number of bytes sent.

        Raises:
            SendError: If sending fails.
        """
        pass

    @abstractmethod
    def get_transport_type(self) -> str:
        """Get the type/name of this transport implementation.

        Returns:
            String identifier for the transport type.
        """
        pass

    def __enter__(self) -> TransportBase:
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        """Context manager exit."""
        self.disconnect()
