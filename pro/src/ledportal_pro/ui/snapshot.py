"""Snapshot saving functionality."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ledportal_utils import LedMode, export_4x6_pdf, export_pdf
from numpy.typing import NDArray

from .overlay import PreviewAlgorithm

# Map pro PreviewAlgorithm to utils LedMode.
# CIRCLES is resolved at call time using led_size_pct.
_ALGORITHM_TO_LED_MODE: dict[PreviewAlgorithm, LedMode] = {
    PreviewAlgorithm.SQUARES: LedMode.SQUARES,
    PreviewAlgorithm.GAUSSIAN_RAW: LedMode.GAUSSIAN,
    PreviewAlgorithm.GAUSSIAN_DIFFUSED: LedMode.GAUSSIAN,
}

# Ordered thresholds for mapping led_size_pct → LedMode circle variant.
_CIRCLE_PCT_MODES: list[tuple[int, LedMode]] = [
    (62, LedMode.CIRCLES_50),
    (87, LedMode.CIRCLES_75),
    (112, LedMode.CIRCLES_100),
    (137, LedMode.CIRCLES_125),
    (999, LedMode.CIRCLES_CORNER),
]


def _resolve_led_mode(algorithm: PreviewAlgorithm, led_size_pct: int) -> LedMode:
    """Convert a PreviewAlgorithm + led_size_pct to the closest LedMode."""
    if algorithm != PreviewAlgorithm.CIRCLES:
        return _ALGORITHM_TO_LED_MODE.get(algorithm, LedMode.SQUARES)
    for threshold, mode in _CIRCLE_PCT_MODES:
        if led_size_pct <= threshold:
            return mode
    return LedMode.CIRCLES_CORNER  # unreachable: last threshold is 999


def _dispatch_print(pdf_path: Path) -> None:
    """Send a PDF to the default printer via lpr. No-ops on non-macOS platforms."""
    if sys.platform != "darwin":
        return
    print("  Sending to printer...")
    subprocess.run(
        [
            "lpr",
            "-o",
            "media=Custom.4x6in",
            "-o",
            "fit-to-page",
            "-o",
            "landscape",
            str(pdf_path),
        ],
        check=False,  # Don't crash the app if no printer is available
    )


class SnapshotManager:
    """Manages saving snapshots of camera frames."""

    def __init__(self, output_dir: Path | str | None = None) -> None:
        """Initialize snapshot manager.

        Args:
            output_dir: Directory to save snapshots. Defaults to current directory.
        """
        self._output_dir = Path(output_dir) if output_dir else Path.cwd()
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def output_dir(self) -> Path:
        """Get output directory path."""
        return self._output_dir

    def save(
        self,
        frame: NDArray[np.uint8],
        frame_bytes: bytes | None = None,
        orientation: str = "landscape",
        prefix: str = "snapshot",
        debug_mode: bool = False,
        original_frame: NDArray[np.uint8] | None = None,
        render_algorithm: PreviewAlgorithm = PreviewAlgorithm.SQUARES,
        led_size_pct: int = 100,
        export_pdf_flag: bool = True,
        export_4x6: bool = False,
        auto_print: bool = False,
    ) -> tuple[Path, Path | None, Path | None, Path | None]:
        """Save a snapshot of the current frame.

        Args:
            frame: BGR image as numpy array (64x32 with rotation applied).
            frame_bytes: Optional RGB565 bytes to save alongside.
            orientation: Display orientation ("landscape" or "portrait").
            prefix: Filename prefix.
            debug_mode: If True, save debug files (raw BMP + RGB565 binary).
            original_frame: Optional original camera frame (full resolution, BGR).
                When provided, it is included in the generated PDF.
            render_algorithm: Current LED preview algorithm (used for PDF rendering).
            led_size_pct: Current LED size percentage (used for circle modes).
            export_pdf_flag: If True (default), generate a Letter-page multi-format PDF.
            export_4x6: If True, generate a 4×6 photo-booth PDF saved to disk.
            auto_print: If True, generate a 4×6 PDF and send it to the default
                printer (macOS only; silently skipped on other platforms). Implies
                export_4x6.

        Returns:
            Tuple of (snapshot_path, debug_image_path or None, rgb565_path or None,
            pdf_path or None).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create properly oriented snapshot for viewing on PC
        if orientation == "portrait":
            # Rotate back 90° CCW so it appears upright (32x64 tall)
            viewer_frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            # Landscape stays as-is (64x32 wide)
            viewer_frame = frame

        # Always save the viewer-oriented snapshot
        snapshot_filename = f"{prefix}_{timestamp}.bmp"
        snapshot_path = self._output_dir / snapshot_filename
        cv2.imwrite(str(snapshot_path), viewer_frame)

        # Debug files (only in debug mode)
        debug_image_path = None
        rgb565_path = None

        if debug_mode:
            # Save raw LED matrix frame (64x32 with rotation applied)
            debug_filename = f"{prefix}_{timestamp}_raw.bmp"
            debug_image_path = self._output_dir / debug_filename
            cv2.imwrite(str(debug_image_path), frame)

            # Save RGB565 binary data
            if frame_bytes is not None:
                rgb565_filename = f"{prefix}_{timestamp}_rgb565.bin"
                rgb565_path = self._output_dir / rgb565_filename
                with open(rgb565_path, "wb") as f:
                    f.write(frame_bytes)

        # Save original camera frame for inclusion in Letter PDF
        original_path = None
        if original_frame is not None:
            original_filename = f"{prefix}_{timestamp}_original.png"
            original_path = self._output_dir / original_filename
            cv2.imwrite(str(original_path), original_frame)

        led_mode = _resolve_led_mode(render_algorithm, led_size_pct)

        # Letter-page multi-format PDF
        pdf_path = None
        if export_pdf_flag:
            pdf_path = export_pdf(
                snapshot_path,
                original_path=original_path,
                mode=led_mode,
            )

        # 4×6 photo-booth PDF (auto_print implies export_4x6)
        if export_4x6 or auto_print:
            path_4x6 = export_4x6_pdf(snapshot_path, mode=led_mode)
            print(f"  4×6 PDF: {path_4x6}")
            if auto_print:
                _dispatch_print(path_4x6)

        return snapshot_path, debug_image_path, rgb565_path, pdf_path

    def save_debug_frame(self, frame: NDArray[np.uint8], filename: str = "last.bmp") -> Path:
        """Save a debug frame (overwrites previous).

        Args:
            frame: BGR image as numpy array.
            filename: Output filename.

        Returns:
            Path to saved file.
        """
        path = self._output_dir / filename
        cv2.imwrite(str(path), frame)
        return path
