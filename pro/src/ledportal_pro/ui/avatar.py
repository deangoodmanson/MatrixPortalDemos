"""Avatar capture mode for guided multi-pose capture sessions.

This module provides a guided avatar capture workflow that walks users
through capturing multiple poses with voice prompts for creating
animated digital avatars.

ADVANCED CONCEPTS:
==================
- State machine pattern for managing capture flow
- JSON serialization for session metadata
- Structured data collection with typed dataclasses
"""

import json
import select
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2

from ..processing import apply_zoom_crop
from .tts import speak

if TYPE_CHECKING:
    from ..capture.base import CameraBase
    from ..config import AppConfig
    from ..transport.base import TransportBase


# Avatar pose definitions: (angle, expression, voice_prompt)
AVATAR_POSES: list[tuple[str, str, str]] = [
    # Front facing
    ("front", "neutral", "Front facing, neutral expression"),
    ("front", "smile", "Front facing, give me a smile"),
    ("front", "smile_open", "Front facing, smile with teeth"),
    ("front", "eyebrows_up", "Front facing, raise your eyebrows"),
    ("front", "eyes_closed", "Front facing, close your eyes"),
    # Left 45 degrees
    ("left", "neutral", "Turn left 45 degrees, neutral"),
    ("left", "smile", "Stay left, give me a smile"),
    ("left", "eyebrows_up", "Stay left, raise your eyebrows"),
    # Right 45 degrees
    ("right", "neutral", "Turn right 45 degrees, neutral"),
    ("right", "smile", "Stay right, give me a smile"),
    ("right", "eyebrows_up", "Stay right, raise your eyebrows"),
    # Up tilt
    ("up", "neutral", "Tilt chin up slightly, neutral"),
    ("up", "smile", "Stay tilted up, smile"),
    # Down tilt
    ("down", "neutral", "Tilt chin down slightly, neutral"),
    ("down", "smile", "Stay tilted down, smile"),
    # Mouth shapes for animation
    ("front", "mouth_o", "Front facing, make an O shape with your mouth"),
    ("front", "mouth_ee", "Front facing, say cheese, hold the ee sound"),
    ("front", "mouth_closed", "Front facing, lips together"),
    # Additions to reach 25 poses
    ("front", "furrowed", "Front facing, furrow your brows like you're concentrating"),
    ("left", "eyes_closed", "Stay left, close your eyes"),
    ("left", "mouth_o", "Stay left, make an O shape with your mouth"),
    ("right", "eyes_closed", "Stay right, close your eyes"),
    ("right", "mouth_o", "Stay right, make an O shape with your mouth"),
    ("up", "eyebrows_up", "Chin tilted up, raise your eyebrows"),
    ("down", "eyebrows_up", "Chin tilted down, raise your eyebrows"),
]

BURST_SIZE: int = 5


@dataclass
class CapturedPose:
    """Information about a captured pose."""

    pose_number: int
    angle: str
    expression: str
    filename: str
    raw_filename: str
    sharpness_score: float
    burst_size: int


@dataclass
class AvatarSession:
    """Metadata for an avatar capture session."""

    session_time: str
    total_poses: int
    captured: list[CapturedPose] = field(default_factory=list)
    skipped: list[dict[str, str | int]] = field(default_factory=list)


class AvatarCaptureManager:
    """Manages guided avatar capture sessions.

    This class implements a state machine for walking users through
    the avatar capture process with voice prompts and organized output.
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        """Initialize avatar capture manager.

        Args:
            output_dir: Base directory for avatar sessions. Defaults to cwd.
        """
        self._output_dir = output_dir or Path.cwd()

    def run_capture_session(
        self,
        camera: CameraBase,
        transport: TransportBase | None,
        config: AppConfig,
        orientation: str,
        processing_mode: str,
        zoom_level: float,
        resize_fn: Callable[..., Any],
        convert_fn: Callable[..., Any],
    ) -> AvatarSession:
        """Run a complete avatar capture session.

        Args:
            camera: Camera instance for capturing frames.
            transport: Transport for sending to display (may be None).
            config: Application configuration.
            orientation: Current orientation (landscape/portrait).
            processing_mode: Current processing mode (center/stretch/fit).
            zoom_level: Current zoom level (0.25-1.0).
            resize_fn: Function to resize frames.
            convert_fn: Function to convert to RGB565.

        Returns:
            AvatarSession with capture results.
        """
        session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        avatar_dir = self._output_dir / f"avatar_{session_time}"
        avatar_dir.mkdir(parents=True, exist_ok=True)

        session = AvatarSession(
            session_time=session_time,
            total_poses=len(AVATAR_POSES),
        )

        self._print_session_header(avatar_dir)
        speak("Avatar capture mode. Get ready.")
        time.sleep(1)

        for i, (angle, expression, prompt) in enumerate(AVATAR_POSES):
            pose_num = i + 1
            result, sharpness = self._capture_single_pose(
                camera=camera,
                transport=transport,
                config=config,
                orientation=orientation,
                processing_mode=processing_mode,
                zoom_level=zoom_level,
                resize_fn=resize_fn,
                convert_fn=convert_fn,
                avatar_dir=avatar_dir,
                pose_num=pose_num,
                total=len(AVATAR_POSES),
                angle=angle,
                expression=expression,
                prompt=prompt,
            )

            if result == "captured":
                filename = f"avatar_{angle}_{expression}.bmp"
                raw_filename = f"avatar_{angle}_{expression}_raw.png"
                session.captured.append(
                    CapturedPose(
                        pose_number=pose_num,
                        angle=angle,
                        expression=expression,
                        filename=filename,
                        raw_filename=raw_filename,
                        sharpness_score=sharpness,
                        burst_size=BURST_SIZE,
                    )
                )
            elif result == "skipped":
                session.skipped.append({"pose": pose_num, "angle": angle, "expression": expression})
            elif result == "quit":
                break

        self._print_session_summary(session, avatar_dir)
        self._save_manifest(session, avatar_dir)

        return session

    def _capture_single_pose(
        self,
        camera: CameraBase,
        transport: TransportBase | None,
        config: AppConfig,
        orientation: str,
        processing_mode: str,
        zoom_level: float,
        resize_fn: Callable[..., Any],
        convert_fn: Callable[..., Any],
        avatar_dir: Path,
        pose_num: int,
        total: int,
        angle: str,
        expression: str,
        prompt: str,
    ) -> tuple[str, float]:
        """Capture a single pose with voice prompt.

        Returns:
            Tuple of (result, sharpness_score) where result is
            "captured", "skipped", or "quit" and sharpness_score is
            the winning frame's Laplacian variance (0.0 when not captured).
        """
        filename = f"avatar_{angle}_{expression}.bmp"
        filepath = avatar_dir / filename
        raw_filepath = avatar_dir / f"avatar_{angle}_{expression}_raw.png"

        print(f"\n--- Pose {pose_num}/{total}: {angle} - {expression} ---")
        print(f"Prompt: {prompt}")

        speak(prompt)

        small_frame = None
        frame_bytes = None

        while True:
            # Capture and display live preview
            try:
                raw_frame = camera.capture()
                zoomed = apply_zoom_crop(raw_frame, zoom_level) if zoom_level < 1.0 else raw_frame
                small_frame = resize_fn(
                    zoomed, config.matrix, config.processing, orientation, processing_mode
                )
                frame_bytes = convert_fn(small_frame)

                if transport is not None:
                    try:
                        transport.send_frame(frame_bytes)
                    except Exception:
                        pass
            except Exception:
                pass

            # Check for input (non-blocking)
            if select.select([sys.stdin], [], [], 0.01)[0]:
                try:
                    key = sys.stdin.read(1).lower()
                except Exception:
                    continue

                if key == " ":
                    # Burst: capture BURST_SIZE frames, keep the sharpest
                    best_raw: Any = None
                    best_small: Any = None
                    best_bytes: Any = None
                    best_score = -1.0

                    for _ in range(BURST_SIZE):
                        try:
                            raw = camera.capture()
                            zoomed = apply_zoom_crop(raw, zoom_level) if zoom_level < 1.0 else raw
                            small = resize_fn(
                                zoomed,
                                config.matrix,
                                config.processing,
                                orientation,
                                processing_mode,
                            )
                            b = convert_fn(small)
                            gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
                            score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                            if score > best_score:
                                best_score = score
                                best_raw = raw
                                best_small = small
                                best_bytes = b
                        except Exception:
                            continue

                    if best_small is not None and best_bytes is not None:
                        cv2.imwrite(str(filepath), best_small)
                        filepath.with_suffix(".bin").write_bytes(best_bytes)
                        cv2.imwrite(str(raw_filepath), best_raw)

                        print(f"  Captured! (sharpness: {best_score:.0f})")
                        speak("Got it")
                        return "captured", best_score
                    else:
                        speak("Failed, try again")

                elif key == "s":
                    print("  Skipped")
                    speak("Skipped")
                    return "skipped", 0.0

                elif key == "r":
                    speak(prompt)

                elif key == "q":
                    print("\n  Avatar capture cancelled.")
                    speak("Cancelled")
                    return "quit", 0.0

    def _print_session_header(self, avatar_dir: Path) -> None:
        """Print session startup information."""
        print("\n" + "=" * 60)
        print("   AVATAR CAPTURE MODE")
        print("=" * 60)
        print(f"\nCapturing {len(AVATAR_POSES)} poses to: {avatar_dir}/")
        print("\nControls:")
        print("  SPACE = Capture this pose")
        print("  S     = Skip this pose")
        print("  R     = Repeat voice prompt")
        print("  Q     = Quit avatar mode")
        print("\nTip: Use 'P' before starting for portrait mode!")
        print("=" * 60)

    def _print_session_summary(self, session: AvatarSession, avatar_dir: Path) -> None:
        """Print session completion summary."""
        print("\n" + "=" * 60)
        print("   AVATAR CAPTURE COMPLETE!")
        print("=" * 60)
        print(f"\nCaptured: {len(session.captured)} poses")
        print(f"Skipped:  {len(session.skipped)} poses")
        print(f"Location: {avatar_dir}/")

        speak(f"Complete! {len(session.captured)} poses saved.")

    def _save_manifest(self, session: AvatarSession, avatar_dir: Path) -> None:
        """Save session manifest as JSON."""
        manifest = {
            "session": session.session_time,
            "total_poses": session.total_poses,
            "captured": [
                {
                    "pose": p.pose_number,
                    "angle": p.angle,
                    "expression": p.expression,
                    "file": p.filename,
                    "raw_file": p.raw_filename,
                    "sharpness_score": p.sharpness_score,
                    "burst_size": p.burst_size,
                }
                for p in session.captured
            ],
            "skipped": session.skipped,
        }

        manifest_path = avatar_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest saved: {manifest_path}")
