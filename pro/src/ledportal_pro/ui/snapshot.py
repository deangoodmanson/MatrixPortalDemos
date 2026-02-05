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
        prefix: str = "snapshot",
    ) -> tuple[Path, Path | None]:
        """Save a snapshot of the current frame.

        Args:
            frame: BGR image as numpy array.
            frame_bytes: Optional RGB565 bytes to save alongside.
            prefix: Filename prefix.

        Returns:
            Tuple of (image_path, rgb565_path or None).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save color image
        image_filename = f"{prefix}_{timestamp}.bmp"
        image_path = self._output_dir / image_filename
        cv2.imwrite(str(image_path), frame)

        # Save RGB565 data if provided
        rgb565_path = None
        if frame_bytes is not None:
            rgb565_filename = f"{prefix}_{timestamp}_rgb565.bin"
            rgb565_path = self._output_dir / rgb565_filename
            with open(rgb565_path, "wb") as f:
                f.write(frame_bytes)

        return image_path, rgb565_path

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
