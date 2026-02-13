"""Tests for snapshot saving."""

import numpy as np

from ledportal_pro.ui.snapshot import SnapshotManager


class TestSnapshotManager:
    """SnapshotManager creates files in the right place with the right names."""

    def test_output_dir_created(self, tmp_path):
        out = tmp_path / "snapshots"
        manager = SnapshotManager(output_dir=out)
        assert out.exists()
        assert manager.output_dir == out

    def test_save_creates_bmp(self, tmp_path):
        manager = SnapshotManager(output_dir=tmp_path)
        frame = np.zeros((32, 64, 3), dtype=np.uint8)

        image_path, debug_path, rgb565_path = manager.save(frame)

        assert image_path.exists()
        assert image_path.suffix == ".bmp"
        assert image_path.name.startswith("snapshot_")
        # No debug mode → no debug files
        assert debug_path is None
        assert rgb565_path is None

    def test_save_creates_bmp_and_bin_in_debug_mode(self, tmp_path):
        manager = SnapshotManager(output_dir=tmp_path)
        frame = np.zeros((32, 64, 3), dtype=np.uint8)
        raw = b"\x00" * (64 * 32 * 2)

        image_path, debug_path, rgb565_path = manager.save(frame, frame_bytes=raw, debug_mode=True)

        assert image_path.exists()
        assert debug_path is not None
        assert debug_path.exists()
        assert rgb565_path is not None
        assert rgb565_path.exists()
        assert rgb565_path.suffix == ".bin"
        assert rgb565_path.read_bytes() == raw

    def test_save_custom_prefix(self, tmp_path):
        manager = SnapshotManager(output_dir=tmp_path)
        frame = np.zeros((32, 64, 3), dtype=np.uint8)

        image_path, _, _ = manager.save(frame, prefix="avatar_front")

        assert image_path.name.startswith("avatar_front_")

    def test_save_debug_frame_overwrites(self, tmp_path):
        manager = SnapshotManager(output_dir=tmp_path)
        frame1 = np.zeros((32, 64, 3), dtype=np.uint8)
        frame2 = np.full((32, 64, 3), 128, dtype=np.uint8)

        path1 = manager.save_debug_frame(frame1)
        path2 = manager.save_debug_frame(frame2)

        # Same path — debug frame always overwrites
        assert path1 == path2
        assert path2.exists()
