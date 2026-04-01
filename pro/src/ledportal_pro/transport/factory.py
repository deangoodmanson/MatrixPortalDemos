"""Transport factory for creating transport instances."""

from typing import TYPE_CHECKING

from .base import TransportBase
from .serial import SerialTransport, find_matrix_portal_port

if TYPE_CHECKING:
    from ..config import TransportConfig


def create_transport(config: TransportConfig) -> TransportBase:
    """Create transport instance based on config.transport_type.

    Args:
        config: Transport configuration settings.

    Returns:
        TransportBase instance (SerialTransport or PipeTransport).
    """
    if config.transport_type == "pipe":
        from .pipe import PipeTransport

        return PipeTransport(config)
    return SerialTransport(config)


def find_matrix_portal() -> str | None:
    """Find Matrix Portal device.

    Returns:
        Port path if found, None otherwise.
    """
    return find_matrix_portal_port()
