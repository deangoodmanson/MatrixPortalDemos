"""Tests for the exception hierarchy."""

from ledportal_pro.exceptions import (
    CameraCaptureFailed,
    CameraError,
    CameraNotFoundError,
    ConfigError,
    ConfigNotFoundError,
    ConfigValidationError,
    DeviceNotFoundError,
    LEDPortalError,
    SendError,
    TransportError,
)


class TestExceptionHierarchy:
    """All custom exceptions inherit from LEDPortalError."""

    def test_camera_errors_are_ledportal_errors(self):
        assert issubclass(CameraError, LEDPortalError)
        assert issubclass(CameraNotFoundError, CameraError)
        assert issubclass(CameraCaptureFailed, CameraError)

    def test_transport_errors_are_ledportal_errors(self):
        assert issubclass(TransportError, LEDPortalError)
        assert issubclass(DeviceNotFoundError, TransportError)
        assert issubclass(SendError, TransportError)

    def test_config_errors_are_ledportal_errors(self):
        assert issubclass(ConfigError, LEDPortalError)
        assert issubclass(ConfigNotFoundError, ConfigError)
        assert issubclass(ConfigValidationError, ConfigError)

    def test_all_are_catchable_as_base(self):
        """Every leaf exception can be caught as LEDPortalError."""
        leaves = [
            CameraNotFoundError,
            CameraCaptureFailed,
            DeviceNotFoundError,
            SendError,
            ConfigNotFoundError,
            ConfigValidationError,
        ]
        for exc_class in leaves:
            try:
                raise exc_class("test")
            except LEDPortalError:
                pass  # expected
            else:
                raise AssertionError(f"{exc_class.__name__} not caught as LEDPortalError")

    def test_exceptions_carry_message(self):
        err = CameraCaptureFailed("disk full")
        assert str(err) == "disk full"
