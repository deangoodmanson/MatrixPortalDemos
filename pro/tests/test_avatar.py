"""Tests for avatar capture data structures and manifest saving."""

import json

import pytest

from ledportal_pro.ui.avatar import AVATAR_POSES, AvatarCaptureManager, AvatarSession, CapturedPose


class TestAvatarPoses:
    """AVATAR_POSES list has the expected structure and content."""

    def test_pose_count(self):
        assert len(AVATAR_POSES) == 25

    def test_each_pose_is_three_tuple(self):
        for pose in AVATAR_POSES:
            assert len(pose) == 3
            angle, expression, prompt = pose
            assert isinstance(angle, str) and len(angle) > 0
            assert isinstance(expression, str) and len(expression) > 0
            assert isinstance(prompt, str) and len(prompt) > 0

    def test_all_angles_present(self):
        angles = {pose[0] for pose in AVATAR_POSES}
        assert angles == {"front", "left", "right", "up", "down"}

    def test_front_has_most_expressions(self):
        """Front facing is the primary angle — should have the most poses."""
        front_count = sum(1 for a, _, _ in AVATAR_POSES if a == "front")
        other_counts = [
            sum(1 for a, _, _ in AVATAR_POSES if a == angle)
            for angle in ("left", "right", "up", "down")
        ]
        assert front_count > max(other_counts)

    def test_all_angles_have_eyebrows_up(self):
        """Every angle now has at least one eyebrows-up variant."""
        angles = {"front", "left", "right", "up", "down"}
        angles_with_brows_up = {a for a, e, _ in AVATAR_POSES if e == "eyebrows_up"}
        assert angles == angles_with_brows_up

    def test_no_duplicate_angle_expression_pairs(self):
        pairs = [(a, e) for a, e, _ in AVATAR_POSES]
        assert len(pairs) == len(set(pairs)), "Duplicate (angle, expression) found"


class TestAvatarSession:
    """AvatarSession dataclass tracks captures and skips."""

    def test_defaults_to_empty_lists(self):
        session = AvatarSession(session_time="20260101_120000", total_poses=18)
        assert session.captured == []
        assert session.skipped == []

    def test_append_captured_pose(self):
        session = AvatarSession(session_time="20260101_120000", total_poses=25)
        pose = CapturedPose(
            pose_number=1,
            angle="front",
            expression="neutral",
            filename="f.bmp",
            raw_filename="f_raw.png",
            sharpness_score=142.5,
            burst_size=5,
        )
        session.captured.append(pose)
        assert len(session.captured) == 1
        assert session.captured[0].angle == "front"


class TestManifestSaving:
    """_save_manifest writes valid JSON with the right structure."""

    def test_manifest_structure(self, tmp_path):
        manager = AvatarCaptureManager(output_dir=tmp_path)
        avatar_dir = tmp_path / "avatar_test"
        avatar_dir.mkdir()

        session = AvatarSession(session_time="20260201_100000", total_poses=25)
        session.captured.append(
            CapturedPose(
                pose_number=1,
                angle="front",
                expression="neutral",
                filename="avatar_front_neutral.bmp",
                raw_filename="avatar_front_neutral_raw.png",
                sharpness_score=312.7,
                burst_size=5,
            )
        )
        session.skipped.append({"pose": 2, "angle": "front", "expression": "smile"})

        manager._save_manifest(session, avatar_dir)

        manifest_path = avatar_dir / "manifest.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["session"] == "20260201_100000"
        assert data["total_poses"] == 25
        assert len(data["captured"]) == 1
        assert data["captured"][0]["angle"] == "front"
        assert data["captured"][0]["file"] == "avatar_front_neutral.bmp"
        assert len(data["skipped"]) == 1
        assert data["skipped"][0]["expression"] == "smile"

    def test_manifest_includes_sharpness_fields(self, tmp_path):
        manager = AvatarCaptureManager(output_dir=tmp_path)
        avatar_dir = tmp_path / "avatar_test2"
        avatar_dir.mkdir()

        session = AvatarSession(session_time="20260201_110000", total_poses=25)
        session.captured.append(
            CapturedPose(
                pose_number=3,
                angle="left",
                expression="smile",
                filename="avatar_left_smile.bmp",
                raw_filename="avatar_left_smile_raw.png",
                sharpness_score=87.3,
                burst_size=5,
            )
        )

        manager._save_manifest(session, avatar_dir)

        data = json.loads((avatar_dir / "manifest.json").read_text())
        entry = data["captured"][0]
        assert entry["raw_file"] == "avatar_left_smile_raw.png"
        assert entry["sharpness_score"] == pytest.approx(87.3)
        assert entry["burst_size"] == 5
