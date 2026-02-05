"""Custom exceptions for LED Portal Pro."""


class LEDPortalError(Exception):
    """Base exception for LED Portal errors."""

    pass


class CameraError(LEDPortalError):
    """Error related to camera operations."""

    pass


class CameraNotFoundError(CameraError):
    """Camera device could not be found or opened."""

    pass


class CameraCaptureFailed(CameraError):
    """Failed to capture a frame from the camera."""

    pass


class TransportError(LEDPortalError):
    """Error related to transport operations."""

    pass


class DeviceNotFoundError(TransportError):
    """Transport device could not be found."""

    pass


class ConnectionError(TransportError):
    """Failed to establish connection with device."""

    pass


class SendError(TransportError):
    """Failed to send data to device."""

    pass


class ConfigError(LEDPortalError):
    """Error related to configuration."""

    pass


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""

    pass


class ConfigValidationError(ConfigError):
    """Configuration validation failed."""

    pass
