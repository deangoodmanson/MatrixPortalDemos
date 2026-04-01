#!/usr/bin/env python3
"""
Matrix Portal Serial Emulator

Listens on USB serial (or a Unix named pipe) for RGB565 frame data sent by
the ledportal camera app and displays it as an LED matrix visualization.

Protocol (matches matrix-portal/code.py):
  Baud:    4,000,000  (serial mode only)
  Header:  b'IMG1'  (4 bytes)
  Payload: 4,096 bytes  (64 × 32 pixels × 2 bytes each, RGB565 little-endian)

Usage:
  uv run emulator.py                          # auto-detect serial port
  uv run emulator.py /dev/tty.usbmodem1       # specify serial port
  uv run emulator.py --pipe /tmp/ledportal.pipe  # use named pipe (Mac/Linux)
  uv run emulator.py --list                   # show available serial ports

Keys:
  q       Quit
  a       Cycle rendering algorithm
  + / -   Increase / decrease display scale
"""

import argparse
import os
import select
import stat
import sys
import time
from collections import deque

import cv2
import numpy as np
import serial
import serial.tools.list_ports

# ── Protocol constants (must match pro/hs sender and matrix-portal firmware) ──
FRAME_HEADER = b"IMG1"
BAUD_RATE = 4_000_000
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 32
FRAME_SIZE = MATRIX_WIDTH * MATRIX_HEIGHT * 2  # 4,096 bytes

# ── Display defaults ──────────────────────────────────────────────────────────
DEFAULT_SCALE = 10  # 64×32 → 640×320 pixels
MIN_SCALE = 4
MAX_SCALE = 20

# ── Rendering algorithms (same names as overlay.py) ──────────────────────────
ALGORITHMS = ["squares", "circles", "gaussian_raw", "gaussian_diffused"]
ALGORITHM_LABELS = {
    "squares": "Squares",
    "circles": "Circles",
    "gaussian_raw": "Gaussian Raw",
    "gaussian_diffused": "Gaussian Diffused",
}

# Gamma correction LUT — matches pro/src/ledportal_pro/ui/overlay.py
_GAMMA = 2.2
_GAMMA_LUT = np.array(
    [round(255 * (i / 255) ** (1.0 / _GAMMA)) if i > 0 else 0 for i in range(256)],
    dtype=np.uint8,
)


# ── Serial helpers ─────────────────────────────────────────────────────────────

def list_ports() -> None:
    """Print all available serial ports."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return
    print("Available serial ports:")
    for p in ports:
        vid = f"VID:{p.vid:04X}" if p.vid else "VID:----"
        pid = f"PID:{p.pid:04X}" if p.pid else "PID:----"
        print(f"  {p.device:25s}  {vid} {pid}  {p.description}")


def find_matrix_portal() -> str | None:
    """
    Auto-detect a Matrix Portal or Adafruit USB serial device.
    Falls back to the first available port if none matches.
    """
    ADAFRUIT_VID = 0x239A
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if p.vid == ADAFRUIT_VID:
            return p.device
    if ports:
        return ports[0].device
    return None


def open_serial(port: str) -> serial.Serial:
    """
    Open the serial port with the same settings the ledportal app uses.

    DTR and RTS are disabled to prevent resetting CircuitPython devices.
    We skip the 2-second boot wait used by the real app — here we're connecting
    to a device that is already running.
    """
    ser = serial.Serial(
        port,
        baudrate=BAUD_RATE,
        timeout=0.1,
        write_timeout=0.5,
        rtscts=False,
        dsrdtr=False,
    )
    ser.dtr = False  # Don't reset CircuitPython on connect
    ser.rts = False
    time.sleep(0.3)
    ser.reset_input_buffer()
    return ser


# ── Named pipe helpers (Mac/Linux only) ──────────────────────────────────────

def open_pipe(path: str) -> int:
    """
    Create FIFO at path if needed, then open it for reading (non-blocking).

    Using O_NONBLOCK means the open() returns immediately even when no writer
    has connected yet — the main loop handles the "waiting" state gracefully.

    Returns the raw file descriptor (int).
    """
    if not os.path.exists(path):
        os.mkfifo(path)
        print(f"Created pipe at {path}")
    elif not stat.S_ISFIFO(os.stat(path).st_mode):
        raise ValueError(f"{path} exists but is not a named pipe (FIFO)")
    return os.open(path, os.O_RDONLY | os.O_NONBLOCK)


def read_pipe(fd: int, buffer: bytearray) -> str:
    """
    Read available bytes from the pipe fd into buffer without blocking.

    Returns:
      'ok'           — bytes were read (or nothing available, normal)
      'disconnected' — writer closed the pipe (EOF)
    """
    try:
        ready, _, _ = select.select([fd], [], [], 0)
        if not ready:
            return "ok"
        data = os.read(fd, 65536)
        if not data:
            return "disconnected"  # EOF — writer closed the pipe
        buffer.extend(data)
        return "ok"
    except BlockingIOError:
        return "ok"  # No data available yet, perfectly normal


# ── Frame extraction (shared by serial and pipe modes) ────────────────────────

def _extract_frame(buffer: bytearray) -> bytes | None:
    """
    Search buffer for the latest IMG1 header and extract one complete frame.

    Searches from the END so we always get the most recent frame when multiple
    frames have buffered up (same strategy as the firmware).

    Mutates buffer in-place (consumes bytes up through the extracted frame).
    Returns raw RGB565 bytes, or None if no complete frame is available yet.
    """
    # Cap buffer to prevent unbounded growth (keep last 4 frames)
    max_buf = (FRAME_SIZE + len(FRAME_HEADER)) * 4
    if len(buffer) > max_buf:
        buffer[:] = buffer[-max_buf:]

    idx = buffer.rfind(FRAME_HEADER)
    if idx == -1:
        return None

    payload_start = idx + len(FRAME_HEADER)
    payload_end = payload_start + FRAME_SIZE

    if len(buffer) < payload_end:
        return None  # Frame not complete yet

    frame = bytes(buffer[payload_start:payload_end])
    del buffer[:payload_end]
    return frame


# ── Serial frame reception ────────────────────────────────────────────────────

def receive_frame(ser: serial.Serial, buffer: bytearray) -> bytes | None:
    """Drain serial bytes into buffer and extract the latest complete frame."""
    waiting = ser.in_waiting
    if waiting > 0:
        buffer.extend(ser.read(waiting))
    return _extract_frame(buffer)


# ── Color conversion ──────────────────────────────────────────────────────────

def rgb565_to_bgr(frame_bytes: bytes) -> np.ndarray:
    """
    Convert RGB565 little-endian bytes to a (32, 64, 3) BGR uint8 array.

    RGB565 bit layout (matches pro/src/ledportal_pro/processing/color.py):
      Bits 15-11: R (5 bits)
      Bits 10-5:  G (6 bits)
      Bits  4-0:  B (5 bits)
    """
    pixels = np.frombuffer(frame_bytes, dtype="<u2").reshape(MATRIX_HEIGHT, MATRIX_WIDTH)

    r5 = ((pixels >> 11) & 0x1F).astype(np.uint8)
    g6 = ((pixels >> 5) & 0x3F).astype(np.uint8)
    b5 = (pixels & 0x1F).astype(np.uint8)

    # Expand from 5/6-bit to 8-bit by replicating high bits into low bits
    r = (r5 << 3) | (r5 >> 2)
    g = (g6 << 2) | (g6 >> 4)
    b = (b5 << 3) | (b5 >> 2)

    return np.stack([b, g, r], axis=-1)  # BGR order for OpenCV


# ── Rendering ─────────────────────────────────────────────────────────────────

def render_led_preview(frame_bgr: np.ndarray, scale: int, algorithm: str) -> np.ndarray:
    """
    Upscale a 64×32 BGR frame into an LED matrix visualization.

    Algorithms match pro/src/ledportal_pro/ui/overlay.py:
      squares          — nearest-neighbor upscale (fast, crisp pixels)
      circles          — each LED rendered as a filled circle on black
      gaussian_raw     — nearest-neighbor + tight gaussian blur (σ≈18% cell)
      gaussian_diffused — nearest-neighbor + wider gaussian blur (σ≈27% cell)
    """
    h, w = frame_bgr.shape[:2]
    out_h, out_w = h * scale, w * scale

    frame_gamma = _GAMMA_LUT[frame_bgr]

    if algorithm == "squares":
        return cv2.resize(frame_gamma, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    elif algorithm == "circles":
        canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
        radius = max(1, int(scale * 0.45))
        for y in range(h):
            for x in range(w):
                cx = x * scale + scale // 2
                cy = y * scale + scale // 2
                color = (int(frame_gamma[y, x, 0]),
                         int(frame_gamma[y, x, 1]),
                         int(frame_gamma[y, x, 2]))
                cv2.circle(canvas, (cx, cy), radius, color, -1, cv2.LINE_AA)
        return canvas

    elif algorithm in ("gaussian_raw", "gaussian_diffused"):
        upscaled = cv2.resize(frame_gamma, (out_w, out_h), interpolation=cv2.INTER_NEAREST)
        sigma_factor = 0.18 if algorithm == "gaussian_raw" else 0.27
        sigma = scale * sigma_factor
        ksize = max(3, int(sigma * 6) | 1)  # Odd kernel, at least 3
        return cv2.GaussianBlur(upscaled, (ksize, ksize), sigma)

    # Fallback
    return cv2.resize(frame_gamma, (out_w, out_h), interpolation=cv2.INTER_NEAREST)


def draw_overlay(
    image: np.ndarray,
    port: str,
    algorithm: str,
    fps: float,
    frames_received: int,
    scale: int,
) -> None:
    """Draw status text onto the preview image (in-place)."""
    algo_label = ALGORITHM_LABELS[algorithm]
    line1 = f"{port}  |  {algo_label}  |  scale {scale}x"
    line2 = f"{fps:.1f} FPS  ({frames_received} frames)   [a] algorithm  [+/-] scale  [q] quit"

    for line, y in ((line1, 18), (line2, 36)):
        # Dark shadow for readability on any background
        cv2.putText(image, line, (9, y + 1), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(image, line, (9, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (220, 220, 220), 1, cv2.LINE_AA)


def draw_waiting(scale: int, port: str, elapsed: float) -> np.ndarray:
    """Return a blank 'waiting for frames' screen."""
    h, w = MATRIX_HEIGHT * scale, MATRIX_WIDTH * scale
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    dots = "." * (int(elapsed) % 4)
    msg = f"Waiting for frames on {port}{dots}"
    cv2.putText(canvas, msg, (10, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 100, 100), 1, cv2.LINE_AA)
    hint = "Send frames with: uv run ledportal --config config/mac.yaml"
    cv2.putText(canvas, hint, (10, h // 2 + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (60, 60, 60), 1, cv2.LINE_AA)
    return canvas


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Matrix Portal Serial Emulator — receives RGB565 frames and displays as LED matrix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "port", nargs="?",
        help="Serial port to listen on (auto-detected if omitted)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available serial ports and exit",
    )
    parser.add_argument(
        "--scale", type=int, default=DEFAULT_SCALE, metavar="N",
        help=f"Initial display scale factor (default: {DEFAULT_SCALE}, range: {MIN_SCALE}–{MAX_SCALE})",
    )
    parser.add_argument(
        "--algorithm", choices=ALGORITHMS, default="squares",
        help="Initial rendering algorithm (default: squares)",
    )
    parser.add_argument(
        "--pipe",
        type=str,
        default=None,
        metavar="PATH",
        help="Listen on a named pipe instead of serial (Mac/Linux); e.g. /tmp/ledportal.pipe",
    )
    args = parser.parse_args()

    if args.list:
        list_ports()
        return 0

    scale = max(MIN_SCALE, min(MAX_SCALE, args.scale))
    algorithm_idx = ALGORITHMS.index(args.algorithm)

    # ── Pipe mode ────────────────────────────────────────────────────────────
    if args.pipe:
        pipe_path = args.pipe
        label = pipe_path  # Shown in overlay instead of port name

        print(f"Pipe mode: {pipe_path}")
        try:
            pipe_fd = open_pipe(pipe_path)
        except (ValueError, OSError) as e:
            print(f"Error: {e}")
            return 1

        print("Waiting for camera app to connect (start it with --pipe)...")
        print("Press 'q' to quit.")

        win_name = "Matrix Portal Emulator (pipe)"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

        buffer: bytearray = bytearray()
        frame_times: deque[float] = deque(maxlen=30)
        last_frame_bgr: np.ndarray | None = None
        frames_received = 0
        start_time = time.monotonic()
        writer_connected = False

        try:
            while True:
                if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) < 1:
                    break

                status = read_pipe(pipe_fd, buffer)
                if status == "disconnected":
                    if writer_connected:
                        print("\nCamera app disconnected. Waiting for reconnect...")
                        writer_connected = False
                    # Reopen the FIFO so a new writer can connect
                    os.close(pipe_fd)
                    pipe_fd = open_pipe(pipe_path)
                else:
                    if not writer_connected and len(buffer) > 0:
                        print("\nCamera app connected!")
                        writer_connected = True

                frame_bytes = _extract_frame(buffer)
                if frame_bytes is not None:
                    frames_received += 1
                    frame_times.append(time.monotonic())
                    last_frame_bgr = rgb565_to_bgr(frame_bytes)

                fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0]) if len(frame_times) >= 2 else 0.0

                if last_frame_bgr is not None:
                    preview = render_led_preview(last_frame_bgr, scale, ALGORITHMS[algorithm_idx])
                    draw_overlay(preview, label, ALGORITHMS[algorithm_idx], fps, frames_received, scale)
                else:
                    elapsed = time.monotonic() - start_time
                    preview = draw_waiting(scale, label, elapsed)

                cv2.imshow(win_name, preview)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord("a"):
                    algorithm_idx = (algorithm_idx + 1) % len(ALGORITHMS)
                    print(f"Algorithm: {ALGORITHM_LABELS[ALGORITHMS[algorithm_idx]]}")
                elif key in (ord("+"), ord("=")):
                    scale = min(MAX_SCALE, scale + 1)
                    cv2.resizeWindow(win_name, MATRIX_WIDTH * scale, MATRIX_HEIGHT * scale)
                elif key == ord("-"):
                    scale = max(MIN_SCALE, scale - 1)
                    cv2.resizeWindow(win_name, MATRIX_WIDTH * scale, MATRIX_HEIGHT * scale)

        except KeyboardInterrupt:
            pass
        finally:
            os.close(pipe_fd)
            cv2.destroyAllWindows()

        print(f"\nDone. Received {frames_received} frames total.")
        return 0

    # ── Serial mode ───────────────────────────────────────────────────────────
    port = args.port or find_matrix_portal()
    if port is None:
        print("Error: No serial port found. Use --list to see available ports.")
        print("       Or specify a port: uv run emulator.py /dev/tty.usbmodemXXXX")
        print("       Or use a pipe:     uv run emulator.py --pipe /tmp/ledportal.pipe")
        return 1

    print(f"Opening {port} at {BAUD_RATE:,} baud...")
    try:
        ser = open_serial(port)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("       Use --list to see available ports.")
        return 1

    print(f"Listening for frames. Press 'q' to quit.")
    print(f"Algorithm: {ALGORITHM_LABELS[ALGORITHMS[algorithm_idx]]}  Scale: {scale}x")

    win_name = "Matrix Portal Emulator"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

    buffer = bytearray()
    frame_times = deque(maxlen=30)
    last_frame_bgr = None
    frames_received = 0
    start_time = time.monotonic()

    try:
        while True:
            if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) < 1:
                break

            try:
                frame_bytes = receive_frame(ser, buffer)
            except serial.SerialException as e:
                print(f"\nSerial error: {e}")
                break

            if frame_bytes is not None:
                frames_received += 1
                frame_times.append(time.monotonic())
                last_frame_bgr = rgb565_to_bgr(frame_bytes)

            fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0]) if len(frame_times) >= 2 else 0.0

            if last_frame_bgr is not None:
                preview = render_led_preview(last_frame_bgr, scale, ALGORITHMS[algorithm_idx])
                draw_overlay(preview, port, ALGORITHMS[algorithm_idx], fps, frames_received, scale)
            else:
                elapsed = time.monotonic() - start_time
                preview = draw_waiting(scale, port, elapsed)

            cv2.imshow(win_name, preview)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("a"):
                algorithm_idx = (algorithm_idx + 1) % len(ALGORITHMS)
                print(f"Algorithm: {ALGORITHM_LABELS[ALGORITHMS[algorithm_idx]]}")
            elif key in (ord("+"), ord("=")):
                scale = min(MAX_SCALE, scale + 1)
                cv2.resizeWindow(win_name, MATRIX_WIDTH * scale, MATRIX_HEIGHT * scale)
                print(f"Scale: {scale}x")
            elif key == ord("-"):
                scale = max(MIN_SCALE, scale - 1)
                cv2.resizeWindow(win_name, MATRIX_WIDTH * scale, MATRIX_HEIGHT * scale)
                print(f"Scale: {scale}x")

    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        cv2.destroyAllWindows()

    print(f"\nDone. Received {frames_received} frames total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
