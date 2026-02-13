"""Tests for frame resizing and display modes."""

import numpy as np
import pytest

from ledportal_pro.processing.resize import ORIENTATIONS, PROCESSING_MODES, resize_frame

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_frame(height: int, width: int, color: list[int] | None = None) -> np.ndarray:
    """Create a solid-color BGR frame."""
    if color is None:
        color = [100, 150, 200]
    return np.full((height, width, 3), color, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Output dimensions — every mode must produce (matrix_height, matrix_width, 3)
# ---------------------------------------------------------------------------


class TestOutputDimensions:
    """Every orientation + processing mode combination produces correct output size."""

    @pytest.mark.parametrize("orientation", ORIENTATIONS)
    @pytest.mark.parametrize("processing_mode", PROCESSING_MODES)
    def test_standard_input(self, matrix_config, orientation, processing_mode):
        frame = make_frame(480, 640)
        result = resize_frame(
            frame, matrix_config, orientation=orientation, processing_mode=processing_mode
        )
        assert result.shape == (matrix_config.height, matrix_config.width, 3)

    @pytest.mark.parametrize("orientation", ORIENTATIONS)
    @pytest.mark.parametrize("processing_mode", PROCESSING_MODES)
    def test_square_input(self, matrix_config, orientation, processing_mode):
        frame = make_frame(500, 500)
        result = resize_frame(
            frame, matrix_config, orientation=orientation, processing_mode=processing_mode
        )
        assert result.shape == (matrix_config.height, matrix_config.width, 3)

    @pytest.mark.parametrize("orientation", ORIENTATIONS)
    @pytest.mark.parametrize("processing_mode", PROCESSING_MODES)
    def test_wide_input(self, matrix_config, orientation, processing_mode):
        frame = make_frame(100, 1920)
        result = resize_frame(
            frame, matrix_config, orientation=orientation, processing_mode=processing_mode
        )
        assert result.shape == (matrix_config.height, matrix_config.width, 3)

    @pytest.mark.parametrize("orientation", ORIENTATIONS)
    @pytest.mark.parametrize("processing_mode", PROCESSING_MODES)
    def test_tall_input(self, matrix_config, orientation, processing_mode):
        frame = make_frame(1920, 100)
        result = resize_frame(
            frame, matrix_config, orientation=orientation, processing_mode=processing_mode
        )
        assert result.shape == (matrix_config.height, matrix_config.width, 3)

    @pytest.mark.parametrize("orientation", ORIENTATIONS)
    @pytest.mark.parametrize("processing_mode", PROCESSING_MODES)
    def test_already_target_size(self, matrix_config, orientation, processing_mode):
        frame = make_frame(32, 64)
        result = resize_frame(
            frame, matrix_config, orientation=orientation, processing_mode=processing_mode
        )
        assert result.shape == (32, 64, 3)


# ---------------------------------------------------------------------------
# Mode-specific behaviour
# ---------------------------------------------------------------------------


class TestCenterMode:
    """Center mode crops from center to match aspect ratio."""

    def test_override_takes_priority(self, matrix_config, processing_config):
        """Explicit orientation/processing_mode args override config."""
        processing_config.orientation = "portrait"
        processing_config.processing_mode = "fit"
        frame = make_frame(480, 640)
        result = resize_frame(
            frame,
            matrix_config,
            processing_config,
            orientation="landscape",
            processing_mode="center",
        )
        assert result.shape == (32, 64, 3)

    def test_none_processing_config_defaults(self, matrix_config):
        """None config defaults to landscape + center."""
        frame = make_frame(480, 640)
        result = resize_frame(
            frame, matrix_config, processing_config=None, orientation=None, processing_mode=None
        )
        assert result.shape == (32, 64, 3)


class TestFitMode:
    """Fit mode (letterbox) maintains aspect ratio and fills remainder with black."""

    def test_fit_has_black_bars_on_tall_input(self, matrix_config):
        """A 4:3 input (480x640) into 2:1 matrix -> black bars left & right."""
        frame = make_frame(480, 640, color=[128, 128, 128])
        result = resize_frame(frame, matrix_config, orientation="landscape", processing_mode="fit")

        # 640 wide into 64 wide: scale = 64/640 = 0.1
        # 480 * 0.1 = 48 but matrix height is 32, so scale = 32/480 ≈ 0.067
        # new_w = 640 * 0.067 = 42, new_h = 32
        # x_offset = (64-42)//2 = 11 → columns 0..10 should be black
        assert np.all(result[:, 0] == 0), "Left black bar expected"
        assert np.all(result[:, -1] == 0), "Right black bar expected"

    def test_fit_wide_input_has_top_bottom_bars(self, matrix_config):
        """A very wide input (100x1000) into 64x32 -> black bars top & bottom."""
        frame = make_frame(100, 1000, color=[200, 200, 200])
        result = resize_frame(frame, matrix_config, orientation="landscape", processing_mode="fit")

        # scale = min(64/1000, 32/100) = min(0.064, 0.32) = 0.064
        # new_h = 100*0.064 = 6, y_offset = (32-6)//2 = 13
        # Top rows should be black
        assert np.all(result[0, :] == 0), "Top black bar expected"
        assert np.all(result[-1, :] == 0), "Bottom black bar expected"


class TestStretchMode:
    """Stretch mode distorts entire frame to fit."""

    def test_solid_color_preserved(self, matrix_config):
        """A solid-color frame stays solid after stretch (no black bars)."""
        frame = make_frame(480, 640, color=[50, 100, 150])
        result = resize_frame(
            frame, matrix_config, orientation="landscape", processing_mode="stretch"
        )
        # Every pixel should be close to the input color (interpolation may shift ±1)
        assert np.all(np.abs(result.astype(int) - np.array([50, 100, 150])) <= 1)


class TestPortraitOrientation:
    """Portrait orientation rotates 90° CW."""

    def test_output_is_correct_shape(self, matrix_config):
        frame = make_frame(480, 640)
        result = resize_frame(
            frame, matrix_config, orientation="portrait", processing_mode="center"
        )
        # Shape is still (matrix_height, matrix_width) = (32, 64) after rotation
        assert result.shape == (32, 64, 3)


# ---------------------------------------------------------------------------
# DISPLAY_MODES constant
# ---------------------------------------------------------------------------


def test_constants_are_correct():
    """Verify orientation and processing mode constants."""
    assert set(ORIENTATIONS) == {"landscape", "portrait"}
    assert set(PROCESSING_MODES) == {"center", "stretch", "fit"}
