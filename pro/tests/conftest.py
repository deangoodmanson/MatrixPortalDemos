"""Shared fixtures for LED Portal Pro tests."""

import numpy as np
import pytest

from ledportal_pro.config import CameraConfig, MatrixConfig, ProcessingConfig, TransportConfig


@pytest.fixture
def matrix_config() -> MatrixConfig:
    """Standard 64x32 matrix config."""
    return MatrixConfig(width=64, height=32)


@pytest.fixture
def small_matrix_config() -> MatrixConfig:
    """Small 8x4 matrix for fast tests that inspect pixel values."""
    return MatrixConfig(width=8, height=4)


@pytest.fixture
def processing_config() -> ProcessingConfig:
    """Default processing config."""
    return ProcessingConfig()


@pytest.fixture
def camera_config() -> CameraConfig:
    """Default camera config."""
    return CameraConfig()


@pytest.fixture
def transport_config() -> TransportConfig:
    """Default transport config."""
    return TransportConfig()


@pytest.fixture
def bgr_frame() -> np.ndarray:
    """640x480 BGR frame with a known gradient pattern."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for y in range(480):
        for x in range(640):
            frame[y, x] = [x % 256, y % 256, (x + y) % 256]  # B, G, R
    return frame


@pytest.fixture
def solid_red_frame() -> np.ndarray:
    """64x32 solid red frame (BGR: 0, 0, 255)."""
    frame = np.zeros((32, 64, 3), dtype=np.uint8)
    frame[:, :] = [0, 0, 255]  # BGR red
    return frame


@pytest.fixture
def solid_white_frame() -> np.ndarray:
    """64x32 solid white frame."""
    return np.full((32, 64, 3), 255, dtype=np.uint8)


@pytest.fixture
def solid_black_frame() -> np.ndarray:
    """64x32 solid black frame."""
    return np.zeros((32, 64, 3), dtype=np.uint8)
