"""Tests for snapshot processing functions."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ledportal_utils import export_blocks, export_circles, export_png


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
