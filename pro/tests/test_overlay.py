"""Tests for overlay drawing functions."""

import numpy as np

from ledportal_pro.ui.overlay import (
    PreviewAlgorithm,
    draw_countdown_overlay,
    draw_mode_indicator,
    draw_text_overlay,
    render_led_preview,
)


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
        # At least one pixel should have a non-zero green channel
        # (anti-aliased text may not produce exactly 255)
        assert np.any(result[:, :, 1] > 0)

    def test_portrait_orientation_changes_output(self, matrix_config):
        """Portrait orientation should produce different output than landscape."""
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        result_landscape = draw_countdown_overlay(frame, 3, matrix_config, orientation="landscape")
        result_portrait = draw_countdown_overlay(frame, 3, matrix_config, orientation="portrait")
        # The two orientations should produce different results
        assert not np.array_equal(result_landscape, result_portrait)

    def test_portrait_orientation_draws_something(self, matrix_config):
        """Portrait mode should actually draw text."""
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        result = draw_countdown_overlay(frame, 2, matrix_config, orientation="portrait")
        # Should have changed some pixels
        assert not np.array_equal(result, frame)


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


class TestRenderLedPreview:
    """Tests for render_led_preview with the new algorithm/size API."""

    @staticmethod
    def _test_frame() -> np.ndarray:
        """Small 4x2 test frame with a known gradient pattern."""
        frame = np.zeros((2, 4, 3), dtype=np.uint8)
        for r in range(2):
            for c in range(4):
                frame[r, c] = [(r * 40 + c * 30) % 256, (r * 60 + c * 20) % 256, (r * 80 + c * 10) % 256]
        return frame

    def test_squares_ignores_size(self):
        """SQUARES output is identical regardless of led_size_pct."""
        frame = self._test_frame()
        out_25 = render_led_preview(frame, PreviewAlgorithm.SQUARES, led_size_pct=25, scale=10)
        out_150 = render_led_preview(frame, PreviewAlgorithm.SQUARES, led_size_pct=150, scale=10)
        assert np.array_equal(out_25, out_150)

    def test_circles_output_shape(self):
        """CIRCLES output has the correct (H*scale, W*scale, 3) shape."""
        frame = self._test_frame()
        scale = 10
        result = render_led_preview(frame, PreviewAlgorithm.CIRCLES, led_size_pct=100, scale=scale)
        assert result.shape == (2 * scale, 4 * scale, 3)

    def test_circles_100_black_at_corner(self):
        """Pixel (0,0) should be black for CIRCLES + size=100.

        Radius = 5 at scale=10, but corner (0,0) is distance sqrt(5^2+5^2) ~ 7.07 > 5.
        """
        frame = np.full((2, 4, 3), 128, dtype=np.uint8)
        result = render_led_preview(frame, PreviewAlgorithm.CIRCLES, led_size_pct=100, scale=10)
        assert np.array_equal(result[0, 0], [0, 0, 0])

    def test_circles_25_more_black_than_100(self):
        """25% circles should have more black pixels than 100% circles."""
        frame = np.full((2, 4, 3), 128, dtype=np.uint8)
        out_25 = render_led_preview(frame, PreviewAlgorithm.CIRCLES, led_size_pct=25, scale=10)
        out_100 = render_led_preview(frame, PreviewAlgorithm.CIRCLES, led_size_pct=100, scale=10)
        black_25 = np.sum(np.all(out_25 == 0, axis=2))
        black_100 = np.sum(np.all(out_100 == 0, axis=2))
        assert black_25 > black_100

    def test_gaussian_raw_noop_for_size(self):
        """GAUSSIAN_RAW output is identical regardless of led_size_pct."""
        frame = self._test_frame()
        out_25 = render_led_preview(frame, PreviewAlgorithm.GAUSSIAN_RAW, led_size_pct=25, scale=10)
        out_150 = render_led_preview(frame, PreviewAlgorithm.GAUSSIAN_RAW, led_size_pct=150, scale=10)
        assert np.array_equal(out_25, out_150)

    def test_gaussian_raw_differs_from_diffused(self):
        """GAUSSIAN_RAW and GAUSSIAN_DIFFUSED produce different results."""
        frame = self._test_frame()
        out_raw = render_led_preview(frame, PreviewAlgorithm.GAUSSIAN_RAW, led_size_pct=100, scale=10)
        out_diff = render_led_preview(frame, PreviewAlgorithm.GAUSSIAN_DIFFUSED, led_size_pct=100, scale=10)
        assert not np.array_equal(out_raw, out_diff)
