"""Serial transport implementation for USB CDC communication."""

import time
from typing import TYPE_CHECKING

import serial
import serial.tools.list_ports

from ..exceptions import ConnectionError, DeviceNotFoundError, SendError
from .base import TransportBase

if TYPE_CHECKING:
    from ..config import TransportConfig


class SerialTransport(TransportBase):
    """Transport implementation using USB serial (CDC)."""

    def __init__(self, config: TransportConfig) -> None:
        """Initialize serial transport.

        Args:
            config: Transport configuration settings.
        """
        super().__init__(config)
        self._serial: serial.Serial | None = None
        self._port: str | None = None

    @property
    def port(self) -> str | None:
        """Get the connected port path."""
        return self._port

    def connect(self, port: str | None = None) -> None:
        """Connect to Matrix Portal via serial.

        Args:
            port: Serial port path. If None, auto-detect Matrix Portal.

        Raises:
            DeviceNotFoundError: If Matrix Portal cannot be found.
            ConnectionError: If connection fails.
        """
        if port is None:
            port = find_matrix_portal_port()
            if port is None:
                available = list_serial_ports()
                raise DeviceNotFoundError(f"Matrix Portal not found. Available ports: {available}")

        try:
            self._serial = serial.Serial(
                port,
                baudrate=self._config.baud_rate,
                timeout=self._config.timeout,
                write_timeout=self._config.write_timeout,
                rtscts=False,
                dsrdtr=False,
            )

            # Prevent DTR reset on CircuitPython devices
            # Must be done AFTER opening the port
            self._serial.dtr = False
            self._serial.rts = False

            # Wait for device to boot (CircuitPython takes ~1.5-2s to boot if reset)
            # If device didn't reset, this just ensures stability
            print(f"Waiting for Matrix Portal to be ready...")
            time.sleep(2.0)

            # Flush any boot messages or garbage data
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

            self._port = port
            self._is_connected = True
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to connect to {port}: {e}") from e

    def disconnect(self) -> None:
        """Close the serial connection."""
        if self._serial is not None and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        self._port = None
        self._is_connected = False

    def send_frame(self, frame_data: bytes) -> int:
        """Send frame data via serial.

        Args:
            frame_data: Raw frame bytes (RGB565 format).

        Returns:
            Number of frame bytes sent (excluding header).

        Raises:
            SendError: If serial is not connected or write fails.
        """
        if self._serial is None or not self._serial.is_open:
            raise SendError("Serial port is not open")

        try:
            # Send frame header
            self._serial.write(self._config.frame_header)
            # Send frame data
            bytes_written = self._serial.write(frame_data)
            # Ensure data is sent immediately (flushes OS buffer to serial port)
            self._serial.flush()

            # Small delay to let receiver process the frame
            # Prevents overwhelming the CircuitPython serial buffer on Raspberry Pi
            # At 4M baud, 4100 bytes takes ~8ms; we add 2ms margin for processing
            time.sleep(0.01)  # 10ms safety margin

            return bytes_written
        except serial.SerialException as e:
            raise SendError(f"Failed to send frame: {e}") from e

    def get_transport_type(self) -> str:
        """Get transport type identifier."""
        return "serial"

    def get_actual_baud_rate(self) -> int | None:
        """Get the actual baud rate of the connection.

        Returns:
            Baud rate if connected, None otherwise.
        """
        if self._serial is not None:
            return self._serial.baudrate
        return None


def find_matrix_portal_port() -> str | None:
    """Find Matrix Portal M4 USB CDC serial port.

    Returns:
        Port path if found, None otherwise.
    """
    ports = serial.tools.list_ports.comports()
    matrix_ports = []

    for port in ports:
        description = port.description or ""
        if "CircuitPython" in description or "Matrix Portal" in description:
            matrix_ports.append(port)

    if not matrix_ports:
        return None

    # If multiple ports, use the one with higher number (typically the data port)
    if len(matrix_ports) > 1:
        matrix_ports.sort(key=lambda p: p.device)
        return matrix_ports[-1].device

    return matrix_ports[0].device


def list_serial_ports() -> list[dict[str, str]]:
    """List all available serial ports.

    Returns:
        List of dictionaries with port information.
    """
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append(
            {
                "device": port.device,
                "description": port.description or "Unknown",
                "hwid": port.hwid or "Unknown",
            }
        )
    return ports
