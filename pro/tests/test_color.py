"""Tests for color conversion and manipulation."""

import numpy as np

from ledportal_pro.processing.color import (
    apply_gamma_correction,
    apply_grayscale,
    convert_to_rgb565,
    rgb565_to_bgr,
)


class TestConvertToRgb565:
    """RGB565 encoding produces correct byte output."""

    def test_output_length(self, solid_red_frame):
        result = convert_to_rgb565(solid_red_frame)
        # 64 * 32 pixels * 2 bytes each
        assert len(result) == 64 * 32 * 2

    def test_black_frame_is_all_zeros(self, solid_black_frame):
        result = convert_to_rgb565(solid_black_frame)
        assert all(b == 0 for b in result)

    def test_white_frame_all_bits_set(self, solid_white_frame):
        """Pure white (255,255,255) -> R=31, G=63, B=31 -> 0xFFFF."""
        result = convert_to_rgb565(solid_white_frame)
        pixels = np.frombuffer(result, dtype="<u2")
        assert np.all(pixels == 0xFFFF)

    def test_pure_red_encoding(self):
        """BGR (0,0,255) = RGB red. R=31, G=0, B=0 -> 0xF800."""
        frame = np.zeros((1, 1, 3), dtype=np.uint8)
        frame[0, 0] = [0, 0, 255]  # BGR red
        result = convert_to_rgb565(frame)
        pixel = np.frombuffer(result, dtype="<u2")[0]
        assert pixel == 0xF800  # 11111 000000 00000

    def test_pure_green_encoding(self):
        """BGR (0,255,0) = RGB green. R=0, G=63, B=0 -> 0x07E0."""
        frame = np.zeros((1, 1, 3), dtype=np.uint8)
        frame[0, 0] = [0, 255, 0]  # BGR green
        result = convert_to_rgb565(frame)
        pixel = np.frombuffer(result, dtype="<u2")[0]
        assert pixel == 0x07E0  # 00000 111111 00000

    def test_pure_blue_encoding(self):
        """BGR (255,0,0) = RGB blue. R=0, G=0, B=31 -> 0x001F."""
        frame = np.zeros((1, 1, 3), dtype=np.uint8)
        frame[0, 0] = [255, 0, 0]  # BGR blue
        result = convert_to_rgb565(frame)
        pixel = np.frombuffer(result, dtype="<u2")[0]
        assert pixel == 0x001F  # 00000 000000 11111


class TestRoundTrip:
    """Converting to RGB565 and back loses only quantization bits."""

    def test_pure_colors_survive_round_trip(self):
        """Primary colors quantize cleanly at max levels."""
        for bgr_color, label in [
            ([0, 0, 255], "red"),
            ([0, 255, 0], "green"),
            ([255, 0, 0], "blue"),
            ([255, 255, 255], "white"),
            ([0, 0, 0], "black"),
        ]:
            frame = np.full((1, 1, 3), bgr_color, dtype=np.uint8)
            encoded = convert_to_rgb565(frame)
            decoded = rgb565_to_bgr(encoded, width=1, height=1)

            # RGB565 quantization: R/B lose low 3 bits, G loses low 2 bits
            expected_b = (bgr_color[0] >> 3) << 3
            expected_g = (bgr_color[1] >> 2) << 2
            expected_r = (bgr_color[2] >> 3) << 3
            assert list(decoded[0, 0]) == [expected_b, expected_g, expected_r], label

    def test_round_trip_shape_preserved(self):
        frame = np.zeros((10, 20, 3), dtype=np.uint8)
        encoded = convert_to_rgb565(frame)
        decoded = rgb565_to_bgr(encoded, width=20, height=10)
        assert decoded.shape == (10, 20, 3)


class TestApplyGrayscale:
    """Grayscale conversion produces equal BGR channels."""

    def test_output_shape_unchanged(self, solid_red_frame):
        result = apply_grayscale(solid_red_frame)
        assert result.shape == solid_red_frame.shape

    def test_black_stays_black(self, solid_black_frame):
        result = apply_grayscale(solid_black_frame)
        assert np.all(result == 0)

    def test_white_stays_white(self, solid_white_frame):
        result = apply_grayscale(solid_white_frame)
        assert np.all(result == 255)

    def test_channels_are_equal(self, solid_red_frame):
        """After grayscale, R == G == B for every pixel."""
        result = apply_grayscale(solid_red_frame)
        assert np.array_equal(result[:, :, 0], result[:, :, 1])
        assert np.array_equal(result[:, :, 1], result[:, :, 2])

    def test_colored_input_produces_nonzero_gray(self):
        """A bright color should not become black."""
        frame = np.full((4, 4, 3), [100, 150, 200], dtype=np.uint8)
        result = apply_grayscale(frame)
        assert result[0, 0, 0] > 0  # grayscale value is nonzero


class TestApplyGammaCorrection:
    """Gamma correction lookup table is applied correctly."""

    def test_output_shape_unchanged(self, solid_red_frame):
        result = apply_gamma_correction(solid_red_frame, gamma=2.2)
        assert result.shape == solid_red_frame.shape

    def test_black_stays_black(self, solid_black_frame):
        result = apply_gamma_correction(solid_black_frame, gamma=2.2)
        assert np.all(result == 0)

    def test_white_stays_white(self, solid_white_frame):
        result = apply_gamma_correction(solid_white_frame, gamma=2.2)
        assert np.all(result == 255)

    def test_gamma_gt1_darkens_midtones(self):
        """Gamma > 1 should brighten mid-range values (inverse gamma applied)."""
        frame = np.full((1, 1, 3), 128, dtype=np.uint8)
        result = apply_gamma_correction(frame, gamma=2.2)
        # inv_gamma = 1/2.2 ≈ 0.45; (128/255)^0.45 * 255 ≈ 186
        assert result[0, 0, 0] > 128
