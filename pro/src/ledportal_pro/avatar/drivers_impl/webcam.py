"""Webcam-driven avatar expression driver.

Uses MediaPipe Face Landmarker (Tasks API) on a live OpenCV camera stream.
Blendshape coefficients map to eye/mouth semantics; the facial transformation
matrix provides yaw/pitch for angle.

Requires the ``mediapipe`` extra:
    uv pip install 'ledportal-pro[avatar]'

And a face_landmarker.task model file:
    uv run ledportal-avatar build --download-model <session_dir>
"""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from ..drivers import DriverState

# ------------------------------------------------------------------ #
# Blendshape thresholds (starting values — tune after real-face test) #
# ------------------------------------------------------------------ #

_BLINK_THRESH = 0.55  # eyeBlinkLeft/Right avg → "closed"
_BROW_UP_THRESH = 0.30  # browInnerUp + browOuterUp* avg → "raised"
_BROW_DOWN_THRESH = 0.30  # browDownLeft/Right avg → "furrowed"

_JAW_OPEN_THRESH = 0.40  # jawOpen → "o"
_SMILE_THRESH = 0.35  # mouthSmileLeft/Right avg → base for "smile*"
_SMILE_OPEN_JAW = 0.25  # jaw threshold that upgrades smile → "smile_open"
_FUNNEL_THRESH = 0.30  # mouthFunnel → "ee"

# ------------------------------------------------------------------ #
# Angle thresholds (degrees)                                          #
# ------------------------------------------------------------------ #

_YAW_THRESH = 20.0  # ±20° → left/right
_PITCH_THRESH = 15.0  # ±15° → up/down


def _blendshape_map(scores: dict[str, float]) -> tuple[str, str]:
    """Map a blendshape score dict to (eye_semantic, mouth_semantic)."""
    # --- Eye semantic ---
    blink_avg = (scores.get("eyeBlinkLeft", 0.0) + scores.get("eyeBlinkRight", 0.0)) / 2.0

    brow_up_vals = [
        scores.get("browInnerUp", 0.0),
        scores.get("browOuterUpLeft", 0.0),
        scores.get("browOuterUpRight", 0.0),
    ]
    brow_up_avg = sum(brow_up_vals) / len(brow_up_vals)

    brow_down_avg = (scores.get("browDownLeft", 0.0) + scores.get("browDownRight", 0.0)) / 2.0

    if blink_avg > _BLINK_THRESH:
        eye_sem = "closed"
    elif brow_up_avg > _BROW_UP_THRESH:
        eye_sem = "raised"
    elif brow_down_avg > _BROW_DOWN_THRESH:
        eye_sem = "furrowed"
    else:
        eye_sem = "open"

    # --- Mouth semantic ---
    jaw_open = scores.get("jawOpen", 0.0)
    smile_avg = (scores.get("mouthSmileLeft", 0.0) + scores.get("mouthSmileRight", 0.0)) / 2.0
    mouth_funnel = scores.get("mouthFunnel", 0.0)

    if jaw_open > _JAW_OPEN_THRESH:
        mouth_sem = "o"
    elif smile_avg > _SMILE_THRESH and jaw_open > _SMILE_OPEN_JAW:
        mouth_sem = "smile_open"
    elif smile_avg > _SMILE_THRESH:
        mouth_sem = "smile"
    elif mouth_funnel > _FUNNEL_THRESH:
        mouth_sem = "ee"
    else:
        mouth_sem = "neutral"

    return eye_sem, mouth_sem


def _matrix_to_angle(matrix_4x4: list[float]) -> str:
    """Extract yaw/pitch from a flat 16-element row-major 4×4 matrix → angle name."""
    m = np.array(matrix_4x4, dtype=np.float64).reshape(4, 4)
    r = m[:3, :3]

    # Pitch (X-axis rotation) and yaw (Y-axis rotation) using ZYX Euler decomposition.
    pitch_rad = math.atan2(-r[2, 0], math.sqrt(r[2, 1] ** 2 + r[2, 2] ** 2))
    yaw_rad = math.atan2(r[1, 0], r[0, 0])

    yaw = math.degrees(yaw_rad)
    pitch = math.degrees(pitch_rad)

    if yaw > _YAW_THRESH:
        return "right"
    if yaw < -_YAW_THRESH:
        return "left"
    if pitch < -_PITCH_THRESH:
        return "up"
    if pitch > _PITCH_THRESH:
        return "down"
    return "front"


class WebcamDriver:
    """Face-tracking avatar driver using MediaPipe Face Landmarker.

    Reads frames from a live OpenCV camera, runs face landmark detection,
    and maps blendshape coefficients + head orientation to ``DriverState``.

    Args:
        model_path: Path to the ``face_landmarker.task`` model file.
            Download with ``ledportal-avatar build --download-model``.
        camera_index: OpenCV camera device index (default 0).
    """

    def __init__(
        self,
        model_path: Path,
        camera_index: int = 0,
    ) -> None:
        self._stop = False
        self._frame_ts_ms: int = 0
        self._last_state = DriverState(angle="front", eyes="open", mouth="neutral")

        try:
            import mediapipe as mp  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "WebcamDriver requires mediapipe. "
                "Install with: uv pip install 'ledportal-pro[avatar]'"
            ) from exc

        BaseOptions = mp.tasks.BaseOptions  # type: ignore[attr-defined]
        FaceLandmarker = mp.tasks.vision.FaceLandmarker  # type: ignore[attr-defined]
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions  # type: ignore[attr-defined]
        RunningMode = mp.tasks.vision.RunningMode  # type: ignore[attr-defined]

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.VIDEO,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self._landmarker = FaceLandmarker.create_from_options(options)

        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_index}")

    # ------------------------------------------------------------------ #
    # Driver protocol                                                      #
    # ------------------------------------------------------------------ #

    def poll(self, dt: float) -> DriverState:
        ret, frame_bgr = self._cap.read()
        if not ret or frame_bgr is None:
            return self._last_state

        self._frame_ts_ms += max(1, int(dt * 1000))

        result = self._run_detection(frame_bgr)
        if result is None:
            return self._last_state

        scores = self._extract_scores(result)
        eye_sem, mouth_sem = _blendshape_map(scores)
        angle = self._extract_angle(result)

        self._last_state = DriverState(angle=angle, eyes=eye_sem, mouth=mouth_sem)
        return self._last_state

    def should_stop(self) -> bool:
        return self._stop

    def close(self) -> None:
        self._stop = True
        if self._cap.isOpened():
            self._cap.release()
        self._landmarker.close()

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _run_detection(self, frame_bgr: np.ndarray) -> object | None:
        """Convert BGR frame to MediaPipe image and run detection."""
        import mediapipe as mp  # noqa: PLC0415

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame_rgb,
        )
        result = self._landmarker.detect_for_video(mp_image, self._frame_ts_ms)
        if not result.face_blendshapes:
            return None
        return result

    def _extract_scores(self, result: object) -> dict[str, float]:
        """Flatten blendshape classifications into {name: score} dict."""
        return {
            c.category_name: c.score
            for c in result.face_blendshapes[0]  # type: ignore[union-attr]
        }

    def _extract_angle(self, result: object) -> str:
        """Extract head angle from the first facial transformation matrix."""
        matrices = getattr(result, "facial_transformation_matrixes", None)
        if not matrices:
            return self._last_state.angle or "front"
        flat = np.array(matrices[0], dtype=np.float64).flatten().tolist()
        return _matrix_to_angle(flat)
