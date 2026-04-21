"""CLI entry point for ledportal-avatar.

Subcommands:
    build    Build an avatar asset bundle from a capture session.
    preview  Display the avatar on-screen (no hardware needed).
    play     Push avatar frames to the LED matrix (coming in Phase 3).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    """Entry point registered as ``ledportal-avatar`` in pyproject.toml."""
    parser = argparse.ArgumentParser(
        prog="ledportal-avatar",
        description="Build and play LED Portal avatar assets.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    # ---- build ----
    build_p = sub.add_parser("build", help="Build avatar asset from a capture session directory")
    build_p.add_argument("session_dir", type=Path, metavar="SESSION_DIR")
    build_p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        metavar="DIR",
        help="Output directory (default: <session_dir>/../avatar_asset_<name>)",
    )
    build_p.add_argument(
        "--palette-size",
        "-n",
        type=int,
        default=8,
        metavar="N",
        help="Number of palette colours 4-16 (default: 8)",
    )
    build_p.add_argument(
        "--model",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to face_landmarker.task (uses heuristics if absent)",
    )
    build_p.add_argument(
        "--download-model",
        action="store_true",
        help="Download the MediaPipe Face Landmarker model before building",
    )

    # ---- preview ----
    prev_p = sub.add_parser("preview", help="Preview avatar on screen (no hardware)")
    prev_p.add_argument("asset_dir", type=Path, metavar="ASSET_DIR")
    prev_p.add_argument(
        "--scale",
        type=int,
        default=8,
        metavar="N",
        help="Upscale factor for the 64×32 frame (default: 8)",
    )

    # ---- play ----
    play_p = sub.add_parser("play", help="Push avatar frames to the LED matrix")
    play_p.add_argument("asset_dir", type=Path, metavar="ASSET_DIR")
    play_p.add_argument(
        "--driver",
        choices=["keyboard", "webcam", "audio"],
        default="keyboard",
        metavar="DRIVER",
        help="Input driver: keyboard (default), webcam, or audio",
    )
    play_p.add_argument(
        "--no-blink",
        action="store_true",
        help="Disable automatic blink injection",
    )
    play_p.add_argument(
        "--port",
        type=str,
        default=None,
        metavar="PORT",
        help="Serial port for the LED matrix (e.g. /dev/ttyACM0). Omit for preview-only.",
    )
    play_p.add_argument(
        "--fps",
        type=float,
        default=15.0,
        metavar="FPS",
        help="Target frame rate (default: 15)",
    )
    play_p.add_argument(
        "--webcam-index",
        type=int,
        default=0,
        metavar="N",
        help="Camera device index for --driver webcam (default: 0)",
    )
    play_p.add_argument(
        "--webcam-model",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to face_landmarker.task for --driver webcam "
        "(default: same path used by 'build')",
    )
    play_p.add_argument(
        "--preview",
        action="store_true",
        help="Show a live on-screen preview window while playing",
    )
    play_p.add_argument(
        "--preview-scale",
        type=int,
        default=8,
        metavar="N",
        help="Upscale factor for the preview window (default: 8)",
    )

    args = parser.parse_args()

    if args.command == "build":
        _cmd_build(args)
    elif args.command == "preview":
        _cmd_preview(args)
    elif args.command == "play":
        _cmd_play(args)


def _cmd_build(args: argparse.Namespace) -> None:
    from .builder import build_avatar, default_model_path, download_model

    session_dir = args.session_dir.resolve()
    if not session_dir.is_dir():
        print(f"Error: session directory not found: {session_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output or session_dir.parent / f"avatar_asset_{session_dir.name}"
    model_path = (args.model or default_model_path()).resolve()

    if args.download_model:
        download_model(model_path)

    build_avatar(
        session_dir=session_dir,
        output_dir=output_dir,
        palette_size=args.palette_size,
        model_path=model_path if model_path.exists() else None,
    )


def _cmd_preview(args: argparse.Namespace) -> None:
    from .preview import run_preview

    asset_dir = args.asset_dir.resolve()
    if not asset_dir.is_dir():
        print(f"Error: asset directory not found: {asset_dir}", file=sys.stderr)
        sys.exit(1)

    run_preview(asset_dir, scale=args.scale)


def _cmd_play(args: argparse.Namespace) -> None:
    from .loop import AvatarLoop, BlinkFilter
    from .player import AvatarPlayer
    from .resolver import VariantResolver
    from .schema import AvatarAsset

    asset_dir = args.asset_dir.resolve()
    if not asset_dir.is_dir():
        print(f"Error: asset directory not found: {asset_dir}", file=sys.stderr)
        sys.exit(1)

    if args.driver == "audio":
        print("Error: audio driver not yet implemented.", file=sys.stderr)
        sys.exit(1)

    asset = AvatarAsset.load(asset_dir)

    transport = None
    if args.port:
        try:
            from ..transport.serial_transport import SerialTransport

            transport = SerialTransport(args.port)
        except Exception as exc:  # noqa: BLE001
            print(f"Error opening serial port {args.port!r}: {exc}", file=sys.stderr)
            sys.exit(1)

    preview_scale = args.preview_scale if args.preview else 0
    player = AvatarPlayer(asset, asset_dir, transport=transport, preview_scale=preview_scale)
    resolver = VariantResolver(asset)

    if args.driver == "webcam":
        from .builder import default_model_path
        from .drivers_impl.webcam import WebcamDriver

        model_path = (args.webcam_model or default_model_path()).resolve()
        if not model_path.exists():
            print(
                f"Error: face_landmarker.task not found at {model_path}\n"
                "Download it with: ledportal-avatar build --download-model <session_dir>",
                file=sys.stderr,
            )
            sys.exit(1)
        driver_inner: object = WebcamDriver(model_path=model_path, camera_index=args.webcam_index)
    else:
        from .drivers_impl.keyboard import KeyboardDriver

        driver_inner = KeyboardDriver()

    driver = driver_inner if args.no_blink else BlinkFilter(driver_inner)  # type: ignore[arg-type]

    loop = AvatarLoop(player, driver, resolver, target_fps=args.fps)
    loop.run()

    if transport is not None:
        transport.close()
