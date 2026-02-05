"""Configuration management for LED Portal Pro."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .exceptions import ConfigNotFoundError, ConfigValidationError


@dataclass
class MatrixConfig:
    """LED Matrix display configuration."""

    width: int = 64
    height: int = 32


@dataclass
class CameraConfig:
    """Camera capture configuration."""

    width: int = 640
    height: int = 480
    index: int = 0
    prefer_picamera: bool = True


@dataclass
class TransportConfig:
    """Transport/communication configuration."""

    baud_rate: int = 2_000_000
    timeout: float = 0.1
    write_timeout: float = 0.5
    frame_header: bytes = field(default=b"IMG1")


@dataclass
class ProcessingConfig:
    """Image processing configuration."""

    interpolation: str = "linear"  # "nearest" or "linear"
    enable_gamma_correction: bool = False
    gamma: float = 2.2
    display_mode: str = "landscape"  # "landscape", "portrait", "squish", "letterbox"


@dataclass
class UIConfig:
    """UI/interaction configuration."""

    countdown_duration: float = 0.5
    snapshot_pause_duration: float = 5.0
    enable_frame_limiting: bool = False
    debug_mode: bool = True
    single_keypress: bool = True  # Use single-keypress input (Mac/Linux only)


@dataclass
class AppConfig:
    """Main application configuration."""

    matrix: MatrixConfig = field(default_factory=MatrixConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    transport: TransportConfig = field(default_factory=TransportConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    target_fps: int = 30
    debug_save_frames: bool = False

    @property
    def frame_size_bytes(self) -> int:
        """Calculate frame size in bytes (RGB565 format)."""
        return self.matrix.width * self.matrix.height * 2

    @property
    def frame_time_ms(self) -> float:
        """Calculate target frame time in milliseconds."""
        return 1000.0 / self.target_fps


def load_config(config_path: Path | str | None = None) -> AppConfig:
    """Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file. If None, returns default config.

    Returns:
        AppConfig instance with loaded or default values.

    Raises:
        ConfigNotFoundError: If specified config file doesn't exist.
        ConfigValidationError: If config file is invalid.
    """
    if config_path is None:
        return AppConfig()

    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in config file: {e}") from e

    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> AppConfig:
    """Parse configuration dictionary into AppConfig.

    Args:
        data: Dictionary with configuration values.

    Returns:
        AppConfig instance.
    """
    matrix_data = data.get("matrix", {})
    camera_data = data.get("camera", {})
    transport_data = data.get("transport", {})
    processing_data = data.get("processing", {})
    ui_data = data.get("ui", {})

    # Handle frame_header as string or bytes
    if "frame_header" in transport_data:
        header = transport_data["frame_header"]
        if isinstance(header, str):
            transport_data["frame_header"] = header.encode("utf-8")

    return AppConfig(
        matrix=MatrixConfig(**matrix_data),
        camera=CameraConfig(**camera_data),
        transport=TransportConfig(**transport_data),
        processing=ProcessingConfig(**processing_data),
        ui=UIConfig(**ui_data),
        target_fps=data.get("target_fps", 10),
        debug_save_frames=data.get("debug_save_frames", False),
    )


def save_config(config: AppConfig, config_path: Path | str) -> None:
    """Save configuration to YAML file.

    Args:
        config: AppConfig instance to save.
        config_path: Path where to save the config file.
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "matrix": {"width": config.matrix.width, "height": config.matrix.height},
        "camera": {
            "width": config.camera.width,
            "height": config.camera.height,
            "index": config.camera.index,
            "prefer_picamera": config.camera.prefer_picamera,
        },
        "transport": {
            "baud_rate": config.transport.baud_rate,
            "timeout": config.transport.timeout,
            "write_timeout": config.transport.write_timeout,
            "frame_header": config.transport.frame_header.decode("utf-8"),
        },
        "processing": {
            "interpolation": config.processing.interpolation,
            "enable_gamma_correction": config.processing.enable_gamma_correction,
            "gamma": config.processing.gamma,
            "display_mode": config.processing.display_mode,
        },
        "ui": {
            "countdown_duration": config.ui.countdown_duration,
            "snapshot_pause_duration": config.ui.snapshot_pause_duration,
            "enable_frame_limiting": config.ui.enable_frame_limiting,
            "debug_mode": config.ui.debug_mode,
            "single_keypress": config.ui.single_keypress,
        },
        "target_fps": config.target_fps,
        "debug_save_frames": config.debug_save_frames,
    }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
