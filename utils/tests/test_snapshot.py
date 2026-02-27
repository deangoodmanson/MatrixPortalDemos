"""Tests for snapshot processing functions."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ledportal_utils import LedMode, export_blocks, export_circles, export_led_preview, export_png


class TestExportPng:
    """Test PNG export functionality."""

    def test_creates_png_file(self, sample_bmp: Path) -> None:
        """Should create a PNG file from BMP input."""
        output = export_png(sample_bmp)

        assert output.exists()
        assert output.suffix == ".png"
        assert output.stem == sample_bmp.stem

    def test_output_has_same_dimensions(self, sample_bmp: Path) -> None:
        """PNG output should have same dimensions as input."""
        output = export_png(sample_bmp)

        original = Image.open(sample_bmp)
        converted = Image.open(output)

        assert converted.size == original.size

    def test_preserves_pixel_data(self, solid_color_bmp: Path) -> None:
        """Should preserve exact pixel data during conversion."""
        output = export_png(solid_color_bmp)

        original_array = np.array(Image.open(solid_color_bmp))
        converted_array = np.array(Image.open(output))

        assert np.array_equal(original_array, converted_array)

    def test_custom_output_path(self, sample_bmp: Path, temp_dir: Path) -> None:
        """Should respect custom output path."""
        custom_path = temp_dir / "custom_name.png"
        output = export_png(sample_bmp, output_path=custom_path)

        assert output == custom_path
        assert output.exists()

    def test_returns_path_object(self, sample_bmp: Path) -> None:
        """Should return a Path object."""
        output = export_png(sample_bmp)
        assert isinstance(output, Path)

    def test_accepts_string_input(self, sample_bmp: Path) -> None:
        """Should accept string path as input."""
        output = export_png(str(sample_bmp))
        assert output.exists()


class TestExportBlocks:
    """Test block (pixelated) export functionality."""

    def test_creates_blocks_file(self, sample_bmp: Path) -> None:
        """Should create a blocks PNG file."""
        output = export_blocks(sample_bmp, scale_factor=5)

        assert output.exists()
        assert output.suffix == ".png"
        assert "_blocks" in output.stem

    def test_upscales_by_factor(self, small_bmp: Path) -> None:
        """Should upscale image by specified factor."""
        scale = 10
        output = export_blocks(small_bmp, scale_factor=scale)

        original = Image.open(small_bmp)
        upscaled = Image.open(output)

        expected_width = original.width * scale
        expected_height = original.height * scale

        assert upscaled.size == (expected_width, expected_height)

    def test_creates_sharp_pixels(self, small_bmp: Path) -> None:
        """Should create sharp square pixels (nearest neighbor)."""
        output = export_blocks(small_bmp, scale_factor=4)

        img_array = np.array(Image.open(output))

        # Check that 4x4 blocks have uniform color (no interpolation)
        # Sample a block at position (0, 0)
        block = img_array[0:4, 0:4]
        first_pixel = block[0, 0]

        # All pixels in this 4x4 block should be identical
        assert np.all(block == first_pixel)

    def test_default_scale_factor(self, sample_bmp: Path) -> None:
        """Should use scale factor of 10 by default."""
        output = export_blocks(sample_bmp)

        original = Image.open(sample_bmp)
        upscaled = Image.open(output)

        assert upscaled.width == original.width * 10
        assert upscaled.height == original.height * 10

    def test_custom_output_path(self, sample_bmp: Path, temp_dir: Path) -> None:
        """Should respect custom output path."""
        custom_path = temp_dir / "my_blocks.png"
        output = export_blocks(sample_bmp, output_path=custom_path, scale_factor=5)

        assert output == custom_path
        assert output.exists()

    def test_different_scale_factors(self, small_bmp: Path) -> None:
        """Should handle different scale factors correctly."""
        for scale in [2, 5, 15, 20]:
            output = export_blocks(small_bmp, scale_factor=scale)
            upscaled = Image.open(output)

            original = Image.open(small_bmp)
            assert upscaled.width == original.width * scale
            assert upscaled.height == original.height * scale


class TestExportCircles:
    """Test circle export functionality."""

    def test_creates_circles_file(self, sample_bmp: Path) -> None:
        """Should create a circles PNG file."""
        output = export_circles(sample_bmp, scale_factor=5)

        assert output.exists()
        assert output.suffix == ".png"
        assert "_circles" in output.stem

    def test_upscales_by_factor(self, small_bmp: Path) -> None:
        """Should upscale image by specified factor."""
        scale = 8
        output = export_circles(small_bmp, scale_factor=scale)

        original = Image.open(small_bmp)
        upscaled = Image.open(output)

        expected_width = original.width * scale
        expected_height = original.height * scale

        assert upscaled.size == (expected_width, expected_height)

    def test_has_black_background(self, small_bmp: Path) -> None:
        """Should have black background between circles."""
        output = export_circles(small_bmp, scale_factor=10, led_size_ratio=0.5)

        img_array = np.array(Image.open(output))

        # Check corners of cells (should be background color)
        corner_pixel = img_array[0, 0]
        assert np.array_equal(corner_pixel, [0, 0, 0])  # Black background

    def test_custom_background_color(self, small_bmp: Path) -> None:
        """Should respect custom background color."""
        custom_bg = (50, 100, 150)
        output = export_circles(
            small_bmp, scale_factor=10, led_size_ratio=0.5, background_color=custom_bg
        )

        img_array = np.array(Image.open(output))

        # Check corner pixel for custom background
        corner_pixel = img_array[0, 0]
        assert np.array_equal(corner_pixel, custom_bg)

    def test_led_size_ratio_affects_output(self, solid_color_bmp: Path, temp_dir: Path) -> None:
        """Different LED size ratios should produce different results."""
        # Use explicit output paths to avoid overwriting
        output_tiny = export_circles(
            solid_color_bmp,
            output_path=temp_dir / "tiny.png",
            scale_factor=20,
            led_size_ratio=0.3,
        )
        output_large = export_circles(
            solid_color_bmp,
            output_path=temp_dir / "large.png",
            scale_factor=20,
            led_size_ratio=0.95,
        )

        img_tiny = np.array(Image.open(output_tiny))
        img_large = np.array(Image.open(output_large))

        # Count non-black pixels (colored LED areas)
        non_black_tiny = np.sum(np.any(img_tiny > 0, axis=2))
        non_black_large = np.sum(np.any(img_large > 0, axis=2))

        # Larger ratio should have significantly more colored pixels
        assert non_black_large > non_black_tiny * 1.5  # At least 50% more

    def test_default_parameters(self, sample_bmp: Path) -> None:
        """Should use sensible defaults."""
        output = export_circles(sample_bmp)

        original = Image.open(sample_bmp)
        upscaled = Image.open(output)

        # Default scale factor is 10
        assert upscaled.width == original.width * 10
        assert upscaled.height == original.height * 10

    def test_custom_output_path(self, sample_bmp: Path, temp_dir: Path) -> None:
        """Should respect custom output path."""
        custom_path = temp_dir / "my_circles.png"
        output = export_circles(sample_bmp, output_path=custom_path, scale_factor=5)

        assert output == custom_path
        assert output.exists()

    def test_circles_are_visible(self, solid_color_bmp: Path) -> None:
        """Circles should contain the original pixel colors."""
        output = export_circles(solid_color_bmp, scale_factor=10, led_size_ratio=0.8)

        img_array = np.array(Image.open(output))
        original_array = np.array(Image.open(solid_color_bmp))
        original_color = original_array[0, 0]

        # Center of first cell should have the original color
        center_y = 5  # Middle of 10-pixel cell
        center_x = 5
        center_pixel = img_array[center_y, center_x]

        # Should match original color (within circle)
        assert np.array_equal(center_pixel, original_color)


class TestLedMode:
    """LedMode enum covers all expected render modes."""

    REQUIRED_MODES = {
        "SQUARES",
        "CIRCLES_50",
        "CIRCLES_75",
        "CIRCLES_100",
        "CIRCLES_125",
        "CIRCLES_CORNER",
        "CIRCLES_CORNER_BLEND",
        "GAUSSIAN",
    }

    def test_all_required_modes_exist(self) -> None:
        names = {mode.name for mode in LedMode}
        assert names == self.REQUIRED_MODES

    def test_mode_count(self) -> None:
        assert len(LedMode) == 8


class TestExportLedPreview:
    """Test export_led_preview with all render modes."""

    @pytest.mark.parametrize("mode", list(LedMode))
    def test_creates_output_file(self, small_bmp: Path, mode: LedMode) -> None:
        """All modes should create a valid output PNG file."""
        output = export_led_preview(small_bmp, mode=mode, scale_factor=4)
        assert output.exists()
        assert output.suffix == ".png"

    @pytest.mark.parametrize("mode", list(LedMode))
    def test_output_dimensions(self, small_bmp: Path, mode: LedMode) -> None:
        """All modes should upscale by scale_factor."""
        scale = 4
        output = export_led_preview(small_bmp, mode=mode, scale_factor=scale)
        original = Image.open(small_bmp)
        result = Image.open(output)
        assert result.width == original.width * scale
        assert result.height == original.height * scale

    def test_default_mode_is_squares(self, sample_bmp: Path, temp_dir: Path) -> None:
        """Default mode should produce same result as export_blocks."""
        blocks_out = export_blocks(sample_bmp, scale_factor=10)
        led_out = export_led_preview(
            sample_bmp, output_path=temp_dir / "led_default.png", scale_factor=10
        )
        blocks_arr = np.array(Image.open(blocks_out))
        led_arr = np.array(Image.open(led_out))
        assert np.array_equal(blocks_arr, led_arr)

    def test_squares_mode_matches_blocks(self, sample_bmp: Path, temp_dir: Path) -> None:
        """SQUARES mode should produce identical output to export_blocks."""
        blocks_out = export_blocks(sample_bmp, scale_factor=10)
        led_out = export_led_preview(
            sample_bmp,
            output_path=temp_dir / "led_squares.png",
            mode=LedMode.SQUARES,
            scale_factor=10,
        )
        blocks_arr = np.array(Image.open(blocks_out))
        led_arr = np.array(Image.open(led_out))
        assert np.array_equal(blocks_arr, led_arr)

    @pytest.mark.parametrize("mode", [LedMode.CIRCLES_50, LedMode.CIRCLES_75, LedMode.CIRCLES_100])
    def test_non_overlapping_modes_have_background_at_corner(
        self, small_bmp: Path, mode: LedMode
    ) -> None:
        """Non-overlapping circle modes should have background at cell corners.

        The top-left corner of each cell is at distance 5√2 ≈ 7.07 from its centre.
        All ≤100% modes have radius < 7.07, so that corner pixel must be background.
        """
        bg = (0, 0, 0)
        output = export_led_preview(small_bmp, mode=mode, scale_factor=10, background_color=bg)
        img_array = np.array(Image.open(output))
        corner_pixel = img_array[0, 0]
        assert np.array_equal(corner_pixel, bg)

    @pytest.mark.parametrize("mode", list(LedMode))
    def test_led_color_at_cell_center(self, small_bmp: Path, mode: LedMode) -> None:
        """Centre of the first LED cell should have the original LED's colour.

        With scale=10 the cell centre is at output pixel (5, 5). Every mode
        draws the LED's own colour there (SQUARES via nearest-neighbour;
        circle modes because only the LED's own circle covers its exact centre).
        """
        scale = 10
        output = export_led_preview(small_bmp, mode=mode, scale_factor=scale)
        img_array = np.array(Image.open(output))
        original = np.array(Image.open(small_bmp).convert("RGB"))
        center_y, center_x = scale // 2, scale // 2
        assert np.array_equal(img_array[center_y, center_x], original[0, 0])

    def test_custom_background_color(self, small_bmp: Path) -> None:
        """Custom background colour should appear in gap areas."""
        custom_bg = (50, 100, 150)
        output = export_led_preview(
            small_bmp,
            mode=LedMode.CIRCLES_50,
            scale_factor=10,
            background_color=custom_bg,
        )
        img_array = np.array(Image.open(output))
        # Corner of first cell is in background territory for 50% circles
        assert np.array_equal(img_array[0, 0], custom_bg)

    def test_custom_output_path(self, sample_bmp: Path, temp_dir: Path) -> None:
        """Should respect custom output path."""
        custom_path = temp_dir / "custom_led.png"
        output = export_led_preview(sample_bmp, output_path=custom_path)
        assert output == custom_path
        assert output.exists()

    def test_default_output_name_contains_mode(self, small_bmp: Path) -> None:
        """Default output filename should embed the mode name."""
        output = export_led_preview(small_bmp, mode=LedMode.CIRCLES_75)
        assert "circles_75" in output.stem

    def test_blend_differs_from_painter_for_adjacent_colors(self, temp_dir: Path) -> None:
        """CIRCLES_CORNER_BLEND should differ from CIRCLES_CORNER when adjacent LEDs
        have different colours (overlap zones show blended vs last-drawn colours)."""
        # Create a 4×2 image with alternating red/green columns
        img_array = np.zeros((2, 4, 3), dtype=np.uint8)
        img_array[:, 0] = [255, 0, 0]  # Red
        img_array[:, 1] = [0, 255, 0]  # Green
        img_array[:, 2] = [255, 0, 0]  # Red
        img_array[:, 3] = [0, 255, 0]  # Green
        varied_path = temp_dir / "varied.bmp"
        Image.fromarray(img_array, mode="RGB").save(varied_path, "BMP")

        painter_out = export_led_preview(
            varied_path,
            output_path=temp_dir / "painter.png",
            mode=LedMode.CIRCLES_CORNER,
            scale_factor=10,
        )
        blend_out = export_led_preview(
            varied_path,
            output_path=temp_dir / "blend.png",
            mode=LedMode.CIRCLES_CORNER_BLEND,
            scale_factor=10,
        )
        painter_arr = np.array(Image.open(painter_out))
        blend_arr = np.array(Image.open(blend_out))
        # Adjacent circles of different colours must differ in their overlap zone
        assert not np.array_equal(painter_arr, blend_arr)

    def test_returns_path_object(self, small_bmp: Path) -> None:
        """Should return a Path object."""
        output = export_led_preview(small_bmp, mode=LedMode.CIRCLES_100)
        assert isinstance(output, Path)

    def test_accepts_string_input(self, small_bmp: Path) -> None:
        """Should accept string path as input."""
        output = export_led_preview(str(small_bmp), mode=LedMode.SQUARES)
        assert output.exists()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_file_raises_error(self, temp_dir: Path) -> None:
        """Should raise error for nonexistent input file."""
        nonexistent = temp_dir / "does_not_exist.bmp"

        with pytest.raises(FileNotFoundError):
            export_png(nonexistent)

    def test_all_functions_accept_path_objects(self, sample_bmp: Path) -> None:
        """All functions should accept Path objects."""
        assert export_png(sample_bmp).exists()
        assert export_blocks(sample_bmp, scale_factor=2).exists()
        assert export_circles(sample_bmp, scale_factor=2).exists()

    def test_all_functions_accept_strings(self, sample_bmp: Path) -> None:
        """All functions should accept string paths."""
        bmp_str = str(sample_bmp)

        assert export_png(bmp_str).exists()
        assert export_blocks(bmp_str, scale_factor=2).exists()
        assert export_circles(bmp_str, scale_factor=2).exists()
