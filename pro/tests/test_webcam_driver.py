"""Tests for WebcamDriver — mocked MediaPipe, no live camera or model file."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ledportal_pro.avatar.drivers_impl.webcam import (
    WebcamDriver,
    _blendshape_map,
    _matrix_to_angle,
)

# ------------------------------------------------------------------ #
# Helpers: build fake MediaPipe result objects                        #
# ------------------------------------------------------------------ #


def _blendshape(name: str, score: float) -> MagicMock:
    c = MagicMock()
    c.category_name = name
    c.score = score
    return c


def _result(scores: dict[str, float], yaw_deg: float = 0.0, pitch_deg: float = 0.0) -> MagicMock:
    """Build a fake FaceLandmarkerResult with the given blendshape scores and head angles."""
    classifications = [_blendshape(k, v) for k, v in scores.items()]
    result = MagicMock()
    result.face_blendshapes = [classifications]
    result.facial_transformation_matrixes = [_rotation_matrix(yaw_deg, pitch_deg)]
    return result


def _rotation_matrix(yaw_deg: float, pitch_deg: float) -> list[float]:
    """Build a flat 16-element row-major rotation matrix for the given yaw and pitch.

    Convention: R = Rz(yaw) @ Ry(pitch), matching _matrix_to_angle's extractor.
    Yaw is Z-axis rotation (left/right); pitch is Y-axis rotation (up/down).
    """
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)

    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    # R = Rz(yaw) @ Ry(pitch)
    r = [
        [cy * cp, -sy, cy * sp, 0.0],
        [sy * cp, cy, sy * sp, 0.0],
        [-sp, 0.0, cp, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    return [v for row in r for v in row]


def _make_driver() -> WebcamDriver:
    """Construct a WebcamDriver with mocked MediaPipe and OpenCV."""
    with (
        patch.dict("sys.modules", {"mediapipe": _fake_mediapipe()}),
        patch("cv2.VideoCapture") as mock_cap_cls,
    ):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap_cls.return_value = mock_cap

        driver = WebcamDriver(model_path=Path("fake.task"), camera_index=0)
        driver._cap = mock_cap
        return driver


def _fake_mediapipe() -> MagicMock:
    """Build a minimal fake mediapipe module tree."""
    mp = MagicMock()
    mp.tasks.BaseOptions = MagicMock()
    mp.tasks.vision.FaceLandmarker.create_from_options = MagicMock(return_value=MagicMock())
    mp.tasks.vision.FaceLandmarkerOptions = MagicMock()
    mp.tasks.vision.RunningMode.VIDEO = "VIDEO"
    mp.Image = MagicMock()
    mp.ImageFormat.SRGB = "SRGB"
    return mp


# ------------------------------------------------------------------ #
# _blendshape_map: eye semantics                                      #
# ------------------------------------------------------------------ #


class TestBlendshapeMapEyes:
    def test_high_blink_avg_gives_closed(self):
        eye, _ = _blendshape_map({"eyeBlinkLeft": 0.8, "eyeBlinkRight": 0.8})
        assert eye == "closed"

    def test_blink_below_threshold_not_closed(self):
        eye, _ = _blendshape_map({"eyeBlinkLeft": 0.3, "eyeBlinkRight": 0.3})
        assert eye != "closed"

    def test_brow_up_gives_raised(self):
        eye, _ = _blendshape_map(
            {
                "browInnerUp": 0.5,
                "browOuterUpLeft": 0.4,
                "browOuterUpRight": 0.4,
            }
        )
        assert eye == "raised"

    def test_brow_down_gives_furrowed(self):
        eye, _ = _blendshape_map({"browDownLeft": 0.6, "browDownRight": 0.6})
        assert eye == "furrowed"

    def test_no_signals_gives_open(self):
        eye, _ = _blendshape_map({})
        assert eye == "open"

    def test_blink_takes_priority_over_brow_up(self):
        """High blink should win over raised brows."""
        eye, _ = _blendshape_map(
            {
                "eyeBlinkLeft": 0.9,
                "eyeBlinkRight": 0.9,
                "browInnerUp": 0.8,
            }
        )
        assert eye == "closed"


# ------------------------------------------------------------------ #
# _blendshape_map: mouth semantics                                    #
# ------------------------------------------------------------------ #


class TestBlendshapeMapMouth:
    def test_high_jaw_open_gives_o(self):
        _, mouth = _blendshape_map({"jawOpen": 0.6})
        assert mouth == "o"

    def test_smile_with_jaw_gives_smile_open(self):
        _, mouth = _blendshape_map(
            {
                "mouthSmileLeft": 0.5,
                "mouthSmileRight": 0.5,
                "jawOpen": 0.3,
            }
        )
        assert mouth == "smile_open"

    def test_smile_without_jaw_gives_smile(self):
        _, mouth = _blendshape_map(
            {
                "mouthSmileLeft": 0.5,
                "mouthSmileRight": 0.5,
                "jawOpen": 0.1,
            }
        )
        assert mouth == "smile"

    def test_funnel_gives_ee(self):
        _, mouth = _blendshape_map({"mouthFunnel": 0.5})
        assert mouth == "ee"

    def test_no_signals_gives_neutral(self):
        _, mouth = _blendshape_map({})
        assert mouth == "neutral"

    def test_jaw_open_beats_smile(self):
        """jawOpen above threshold takes priority."""
        _, mouth = _blendshape_map(
            {
                "jawOpen": 0.8,
                "mouthSmileLeft": 0.9,
                "mouthSmileRight": 0.9,
            }
        )
        assert mouth == "o"


# ------------------------------------------------------------------ #
# _matrix_to_angle: angle from rotation matrix                       #
# ------------------------------------------------------------------ #


class TestMatrixToAngle:
    def test_identity_gives_front(self):
        identity = [
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            1,
        ]
        assert _matrix_to_angle(identity) == "front"

    def test_positive_yaw_gives_right(self):
        assert _matrix_to_angle(_rotation_matrix(yaw_deg=25.0, pitch_deg=0.0)) == "right"

    def test_negative_yaw_gives_left(self):
        assert _matrix_to_angle(_rotation_matrix(yaw_deg=-25.0, pitch_deg=0.0)) == "left"

    def test_negative_pitch_gives_up(self):
        assert _matrix_to_angle(_rotation_matrix(yaw_deg=0.0, pitch_deg=-20.0)) == "up"

    def test_positive_pitch_gives_down(self):
        assert _matrix_to_angle(_rotation_matrix(yaw_deg=0.0, pitch_deg=20.0)) == "down"

    def test_small_angles_give_front(self):
        assert _matrix_to_angle(_rotation_matrix(yaw_deg=10.0, pitch_deg=5.0)) == "front"

    def test_at_yaw_threshold_boundary(self):
        # Exactly 20° should still be "right"
        assert _matrix_to_angle(_rotation_matrix(yaw_deg=20.01, pitch_deg=0.0)) == "right"


# ------------------------------------------------------------------ #
# WebcamDriver.poll: integration with mocked detection               #
# ------------------------------------------------------------------ #


class TestWebcamDriverPoll:
    def _driver_with_result(self, fake_result: MagicMock) -> WebcamDriver:
        driver = _make_driver()
        # Inject a fake frame read
        driver._cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        # Inject detection result
        driver._run_detection = MagicMock(return_value=fake_result)
        return driver

    def test_poll_returns_driver_state(self):
        result = _result({"eyeBlinkLeft": 0.1, "eyeBlinkRight": 0.1}, yaw_deg=0.0)
        driver = self._driver_with_result(result)
        state = driver.poll(0.033)
        assert state.angle is not None
        assert state.eyes is not None
        assert state.mouth is not None

    def test_blink_maps_to_closed(self):
        result = _result({"eyeBlinkLeft": 0.9, "eyeBlinkRight": 0.9})
        driver = self._driver_with_result(result)
        state = driver.poll(0.033)
        assert state.eyes == "closed"

    def test_smile_maps_correctly(self):
        result = _result({"mouthSmileLeft": 0.6, "mouthSmileRight": 0.6, "jawOpen": 0.1})
        driver = self._driver_with_result(result)
        state = driver.poll(0.033)
        assert state.mouth == "smile"

    def test_yaw_right_maps_to_right(self):
        result = _result({}, yaw_deg=30.0)
        driver = self._driver_with_result(result)
        state = driver.poll(0.033)
        assert state.angle == "right"

    def test_no_face_detected_returns_last_state(self):
        driver = _make_driver()
        driver._cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        driver._run_detection = MagicMock(return_value=None)
        # Seed a known last state
        driver._last_state.angle = "left"
        state = driver.poll(0.033)
        assert state.angle == "left"

    def test_failed_cap_read_returns_last_state(self):
        driver = _make_driver()
        driver._cap.read.return_value = (False, None)
        state = driver.poll(0.033)
        assert state.angle == "front"  # default initial state


# ------------------------------------------------------------------ #
# WebcamDriver lifecycle                                              #
# ------------------------------------------------------------------ #


class TestWebcamDriverLifecycle:
    def test_should_stop_false_initially(self):
        driver = _make_driver()
        assert not driver.should_stop()

    def test_close_sets_stop(self):
        driver = _make_driver()
        driver.close()
        assert driver.should_stop()

    def test_close_releases_cap(self):
        driver = _make_driver()
        driver._cap.isOpened.return_value = True
        driver.close()
        driver._cap.release.assert_called_once()

    def test_missing_mediapipe_raises_import_error(self):
        with (
            patch.dict("sys.modules", {"mediapipe": None}),
            patch("cv2.VideoCapture"),
            pytest.raises(ImportError, match="mediapipe"),
        ):
            WebcamDriver(model_path=Path("fake.task"))
