"""Tests for overlay drawing functions."""

import numpy as np

from ledportal_pro.config import MatrixConfig
from ledportal_pro.ui.overlay import draw_countdown_overlay, draw_mode_indicator, draw_text_overlay


class TestDrawCountdownOverlay:
    """Countdown overlay returns a modified copy; original is untouched."""

    def test_does_not_mutate_input(self, matrix_config):
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        original_copy = frame.copy()
        draw_countdown_overlay(frame, 3, matrix_config)
        assert np.array_equal(frame, original_copy)

    def test_output_shape_matches_input(self, matrix_config):
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        result = draw_countdown_overlay(frame, 2, matrix_config)
        assert result.shape == frame.shape

    def test_output_differs_from_black_input(self, matrix_config):
        """Drawing on a black frame must change at least one pixel."""
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        result = draw_countdown_overlay(frame, 1, matrix_config)
        assert not np.array_equal(result, frame)

    def test_custom_color_used(self, matrix_config):
        """Specifying a green color should produce green pixels somewhere."""
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        green = (0, 255, 0)
        result = draw_countdown_overlay(frame, 3, matrix_config, color=green)
        # At least one pixel should have the green channel == 255
        assert np.any(result[:, :, 1] == 255)


class TestDrawTextOverlay:
    """Generic text overlay works the same way."""

    def test_does_not_mutate_input(self):
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        original_copy = frame.copy()
        draw_text_overlay(frame, "HI", (5, 15))
        assert np.array_equal(frame, original_copy)

    def test_output_shape_matches(self):
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        result = draw_text_overlay(frame, "TEST", (2, 20))
        assert result.shape == (32, 64, 3)

    def test_drawing_changes_frame(self):
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        result = draw_text_overlay(frame, "X", (10, 20))
        assert not np.array_equal(result, frame)


class TestDrawModeIndicator:
    """Mode indicator drawn in upper-right corner."""

    def test_does_not_mutate_input(self, matrix_config):
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        original_copy = frame.copy()
        draw_mode_indicator(frame, "B&W", matrix_config)
        assert np.array_equal(frame, original_copy)

    def test_output_shape_matches(self, matrix_config):
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        result = draw_mode_indicator(frame, "LB", matrix_config)
        assert result.shape == (32, 64, 3)
