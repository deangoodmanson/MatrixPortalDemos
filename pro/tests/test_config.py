"""Tests for configuration management."""

import pytest
import yaml

from ledportal_pro.config import AppConfig, MatrixConfig, load_config, save_config
from ledportal_pro.exceptions import ConfigNotFoundError, ConfigValidationError


class TestDefaults:
    """AppConfig default values are correct."""

    def test_default_matrix_dimensions(self):
        config = AppConfig()
        assert config.matrix.width == 64
        assert config.matrix.height == 32

    def test_default_camera_resolution(self):
        config = AppConfig()
        assert config.camera.width == 640
        assert config.camera.height == 480
        assert config.camera.index == 0

    def test_default_transport_baud(self):
        config = AppConfig()
        assert config.transport.baud_rate == 2_000_000
        assert config.transport.frame_header == b"IMG1"

    def test_default_orientation_and_processing(self):
        config = AppConfig()
        assert config.processing.orientation == "landscape"
        assert config.processing.processing_mode == "center"

    def test_default_target_fps(self):
        config = AppConfig()
        assert config.target_fps == 30

    def test_frame_size_bytes_property(self):
        config = AppConfig()
        # 64 * 32 * 2 bytes (RGB565)
        assert config.frame_size_bytes == 4096

    def test_frame_time_ms_property(self):
        config = AppConfig()
        assert config.frame_time_ms == pytest.approx(33.33, rel=0.01)  # 1000 / 30 fps


class TestLoadConfig:
    """Loading config from YAML files."""

    def test_load_none_returns_defaults(self):
        config = load_config(None)
        assert config.matrix.width == 64
        assert config.target_fps == 30

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(ConfigNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml_raises(self, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(": : : not valid yaml [[[")
        with pytest.raises(ConfigValidationError):
            load_config(bad_yaml)

    def test_load_empty_yaml_returns_defaults(self, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        config = load_config(empty)
        assert config.matrix.width == 64

    def test_load_partial_overrides(self, tmp_path):
        partial = tmp_path / "partial.yaml"
        partial.write_text(yaml.dump({"matrix": {"width": 128}, "target_fps": 20}))
        config = load_config(partial)
        assert config.matrix.width == 128
        assert config.matrix.height == 32  # default untouched
        assert config.target_fps == 20

    def test_load_frame_header_as_string(self, tmp_path):
        """frame_header in YAML is a string; should be converted to bytes."""
        cfg_file = tmp_path / "header.yaml"
        cfg_file.write_text(yaml.dump({"transport": {"frame_header": "HDR1"}}))
        config = load_config(cfg_file)
        assert config.transport.frame_header == b"HDR1"


class TestSaveAndRoundTrip:
    """Save config to YAML, reload, verify values survive."""

    def test_round_trip_preserves_values(self, tmp_path):
        original = AppConfig()
        original.matrix.width = 128
        original.matrix.height = 64
        original.target_fps = 30
        original.processing.orientation = "portrait"
        original.processing.processing_mode = "fit"

        path = tmp_path / "roundtrip.yaml"
        save_config(original, path)
        loaded = load_config(path)

        assert loaded.matrix.width == 128
        assert loaded.matrix.height == 64
        assert loaded.target_fps == 30
        assert loaded.processing.orientation == "portrait"
        assert loaded.processing.processing_mode == "fit"

    def test_round_trip_preserves_frame_header(self, tmp_path):
        original = AppConfig()
        original.transport.frame_header = b"TEST"

        path = tmp_path / "header_rt.yaml"
        save_config(original, path)
        loaded = load_config(path)

        assert loaded.transport.frame_header == b"TEST"
