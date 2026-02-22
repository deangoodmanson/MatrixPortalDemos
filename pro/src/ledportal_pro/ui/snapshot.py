"""Snapshot saving functionality."""

from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray


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
    ) -> tuple[Path, Path | None, Path | None]:
        """Save a snapshot of the current frame.

        Args:
            frame: BGR image as numpy array (64x32 with rotation applied).
            frame_bytes: Optional RGB565 bytes to save alongside.
            orientation: Display orientation ("landscape" or "portrait").
            prefix: Filename prefix.
            debug_mode: If True, save debug files (raw BMP + RGB565 binary).

        Returns:
            Tuple of (snapshot_path, debug_image_path or None, rgb565_path or None).
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

        return snapshot_path, debug_image_path, rgb565_path

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
