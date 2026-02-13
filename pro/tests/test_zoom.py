"""Tests for zoom crop processing."""

import numpy as np

from ledportal_pro.processing.zoom import apply_zoom_crop


def test_apply_zoom_crop_100_percent():
    """Test that 100% zoom returns unchanged frame."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = apply_zoom_crop(frame, 1.0)

    # Should return the same frame (no-op)
    assert result.shape == frame.shape
    np.testing.assert_array_equal(result, frame)


def test_apply_zoom_crop_50_percent():
    """Test that 50% zoom crops to center half."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = apply_zoom_crop(frame, 0.5)

    # Should be half width and half height
    assert result.shape == (240, 320, 3)


def test_apply_zoom_crop_75_percent():
    """Test that 75% zoom crops to center 75%."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = apply_zoom_crop(frame, 0.75)

    # Should be 75% width and 75% height
    assert result.shape == (360, 480, 3)


def test_apply_zoom_crop_25_percent():
    """Test that 25% zoom crops to center 25%."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = apply_zoom_crop(frame, 0.25)

    # Should be 25% width and 25% height
    assert result.shape == (120, 160, 3)


def test_apply_zoom_crop_centered():
    """Test that crop is centered on original."""
    # Create frame with unique pattern
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    # Mark center with white pixel
    frame[50, 50] = [255, 255, 255]

    # Crop to 50% should include center pixel at new center
    result = apply_zoom_crop(frame, 0.5)

    # New center should be at (25, 25) and should be white
    assert result.shape == (50, 50, 3)
    np.testing.assert_array_equal(result[25, 25], [255, 255, 255])


def test_apply_zoom_crop_preserves_color():
    """Test that zoom preserves color channels."""
    frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
    result = apply_zoom_crop(frame, 0.5)

    # All pixels should still be 128 in all channels
    assert np.all(result == 128)


def test_apply_zoom_crop_over_100_percent():
    """Test that zoom > 100% returns unchanged frame."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = apply_zoom_crop(frame, 1.5)

    # Should return the same frame (clamped to 100%)
    assert result.shape == frame.shape
    np.testing.assert_array_equal(result, frame)
