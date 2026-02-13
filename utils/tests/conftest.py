"""Shared fixtures for ledportal-utils tests."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Temporary directory for test outputs."""
    return tmp_path


@pytest.fixture
def sample_bmp(temp_dir: Path) -> Path:
    """Create a sample 64x32 BMP file for testing."""
    # Create a simple gradient image (64x32)
    width, height = 64, 32
    img_array = np.zeros((height, width, 3), dtype=np.uint8)

    # Create a gradient pattern
    for y in range(height):
        for x in range(width):
            img_array[y, x] = [
                int((x / width) * 255),  # Red gradient
                int((y / height) * 255),  # Green gradient
                128,  # Constant blue
            ]

    # Convert to PIL and save as BMP
    img = Image.fromarray(img_array, mode="RGB")
    bmp_path = temp_dir / "test_snapshot.bmp"
    img.save(bmp_path, "BMP")

    return bmp_path


@pytest.fixture
def small_bmp(temp_dir: Path) -> Path:
    """Create a small 8x4 BMP file for fast tests."""
    # Create a small test image
    width, height = 8, 4
    img_array = np.zeros((height, width, 3), dtype=np.uint8)

    # Simple pattern: red in top half, blue in bottom half
    img_array[0:2, :] = [255, 0, 0]  # Red
    img_array[2:4, :] = [0, 0, 255]  # Blue

    img = Image.fromarray(img_array, mode="RGB")
    bmp_path = temp_dir / "small_snapshot.bmp"
    img.save(bmp_path, "BMP")

    return bmp_path


@pytest.fixture
def solid_color_bmp(temp_dir: Path) -> Path:
    """Create a solid color 32x16 BMP file."""
    img_array = np.full((16, 32, 3), [100, 150, 200], dtype=np.uint8)
    img = Image.fromarray(img_array, mode="RGB")
    bmp_path = temp_dir / "solid_color.bmp"
    img.save(bmp_path, "BMP")

    return bmp_path
