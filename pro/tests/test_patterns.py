"""Tests for test pattern generation."""

import numpy as np

from ledportal_pro.config import MatrixConfig
from ledportal_pro.processing.patterns import (
    create_checkerboard,
    create_color_bars,
    create_solid_color,
    create_test_pattern,
)


def _expected_byte_count(config: MatrixConfig) -> int:
    return config.width * config.height * 2  # RGB565 = 2 bytes/pixel


class TestCreateTestPattern:
    """Gradient test pattern has correct size and non-trivial content."""

    def test_byte_count(self, matrix_config):
        result = create_test_pattern(matrix_config)
        assert len(result) == _expected_byte_count(matrix_config)

    def test_not_all_zeros(self, matrix_config):
        """Gradient pattern must have non-zero pixels."""
        result = create_test_pattern(matrix_config)
        pixels = np.frombuffer(result, dtype="<u2")
        assert np.any(pixels != 0)

    def test_small_matrix(self):
        """Works with unusual dimensions."""
        cfg = MatrixConfig(width=4, height=2)
        result = create_test_pattern(cfg)
        assert len(result) == 4 * 2 * 2


class TestCreateColorBars:
    """Color bars pattern produces correct byte count and distinct columns."""

    def test_byte_count(self, matrix_config):
        result = create_color_bars(matrix_config)
        assert len(result) == _expected_byte_count(matrix_config)

    def test_has_multiple_distinct_values(self, matrix_config):
        """8 color bars → at least 8 distinct pixel values."""
        result = create_color_bars(matrix_config)
        pixels = np.frombuffer(result, dtype="<u2")
        assert len(np.unique(pixels)) >= 8


class TestCreateSolidColor:
    """Solid color frame has uniform pixel values."""

    def test_byte_count(self, matrix_config):
        result = create_solid_color(matrix_config, (0, 0, 0))
        assert len(result) == _expected_byte_count(matrix_config)

    def test_black_is_all_zeros(self, matrix_config):
        result = create_solid_color(matrix_config, (0, 0, 0))
        assert all(b == 0 for b in result)

    def test_solid_color_is_uniform(self, matrix_config):
        """Every pixel in a solid frame is the same RGB565 value."""
        result = create_solid_color(matrix_config, (128, 64, 200))
        pixels = np.frombuffer(result, dtype="<u2")
        assert len(np.unique(pixels)) == 1


class TestCreateCheckerboard:
    """Checkerboard alternates between exactly two colors."""

    def test_byte_count(self, matrix_config):
        result = create_checkerboard(matrix_config)
        assert len(result) == _expected_byte_count(matrix_config)

    def test_default_has_two_colors(self, matrix_config):
        """Default black/white checkerboard has exactly 2 distinct pixel values."""
        result = create_checkerboard(matrix_config)
        pixels = np.frombuffer(result, dtype="<u2")
        assert len(np.unique(pixels)) == 2

    def test_custom_colors_has_two_colors(self, matrix_config):
        result = create_checkerboard(
            matrix_config,
            cell_size=2,
            color1=(255, 0, 0),  # BGR blue
            color2=(0, 0, 255),  # BGR red
        )
        pixels = np.frombuffer(result, dtype="<u2")
        assert len(np.unique(pixels)) == 2
