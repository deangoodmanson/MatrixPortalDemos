"""Pipe transport implementation for Unix named pipe (FIFO) communication."""

import os
import stat
from typing import IO, TYPE_CHECKING

from ..exceptions import ConnectionError, SendError
from .base import TransportBase

if TYPE_CHECKING:
    from ..config import TransportConfig


class PipeTransport(TransportBase):
    """Transport implementation using a Unix named pipe (FIFO).

    The emulator creates the FIFO and opens it for reading; this transport
    opens it for writing.  Opening a FIFO for writing blocks until the reader
    (emulator) is ready, so start the emulator first.
    """

    def __init__(self, config: TransportConfig) -> None:
        """Initialize pipe transport.

        Args:
            config: Transport configuration settings.
        """
        super().__init__(config)
        self._pipe: IO[bytes] | None = None
        self._pipe_path: str | None = None

    @property
    def port(self) -> str | None:
        """Get the connected pipe path."""
        return self._pipe_path

    def connect(self, port: str | None = None) -> None:
        """Open a named pipe (FIFO) for writing.

        If the FIFO does not exist it is created.  Opening blocks until the
        emulator (reader) connects.

        Args:
            port: Pipe path override.  If None, uses config.pipe_path.

        Raises:
            ConnectionError: If the path exists but is not a FIFO, or open fails.
        """
        pipe_path = port or self._config.pipe_path

        # Create FIFO if it doesn't exist
        if not os.path.exists(pipe_path):
            os.mkfifo(pipe_path)
            print(f"  Created pipe at {pipe_path}")
        elif not stat.S_ISFIFO(os.stat(pipe_path).st_mode):
            raise ConnectionError(f"{pipe_path} exists but is not a named pipe (FIFO)")

        print(f"  Pipe at {pipe_path} — waiting for emulator to connect...")
        try:
            # open() on a FIFO for writing blocks until a reader opens the other end
            self._pipe = open(pipe_path, "wb", buffering=0)  # noqa: SIM115
            self._pipe_path = pipe_path
            self._is_connected = True
            print("  Emulator connected via pipe.")
        except OSError as e:
            raise ConnectionError(f"Failed to open pipe {pipe_path}: {e}") from e

    def disconnect(self) -> None:
        """Close the pipe."""
        if self._pipe is not None:
            try:
                self._pipe.close()
            except Exception:
                pass
        self._pipe = None
        self._pipe_path = None
        self._is_connected = False

    def send_frame(self, frame_data: bytes) -> int:
        """Send frame data via named pipe.

        Args:
            frame_data: Raw frame bytes (RGB565 format).

        Returns:
            Number of frame bytes sent (excluding header).

        Raises:
            SendError: If pipe is not open or write fails.
        """
        if self._pipe is None:
            raise SendError("Pipe is not open")

        try:
            self._pipe.write(self._config.frame_header)
            bytes_written = self._pipe.write(frame_data)
            self._pipe.flush()
            return bytes_written
        except BrokenPipeError as e:
            self._is_connected = False
            raise SendError(f"Pipe broken — emulator disconnected: {e}") from e
        except OSError as e:
            raise SendError(f"Failed to send frame via pipe: {e}") from e

    def get_transport_type(self) -> str:
        """Get transport type identifier."""
        return "pipe"
