#!/usr/bin/env python3
"""
Test script to verify camera capture and conversion (macOS).
Saves a test frame to verify the pipeline works.
"""

import cv2
from camera_feed import setup_camera, capture_frame, resize_frame, convert_to_rgb565

def main():
    print("Testing camera capture and conversion...")

    # Setup camera
    camera = setup_camera()
    print("Camera initialized")

    # Capture a frame
    print("Capturing frame...")
    frame = capture_frame(camera)
    if frame is None:
        print("Failed to capture frame!")
        return

    print(f"Captured frame: {frame.shape}")

    # Resize
    small_frame = resize_frame(frame)
    print(f"Resized to: {small_frame.shape}")

    # Convert to RGB565
    frame_bytes = convert_to_rgb565(small_frame)
    print(f"RGB565 bytes: {len(frame_bytes)} bytes")
    print(f"Expected: {64 * 32 * 2} bytes")

    # Save resized frame for visual verification
    cv2.imwrite("test_frame.png", small_frame)
    print("Saved test_frame.png")

    # Cleanup
    camera.release()

    print("\nTest complete! Check test_frame.png to verify camera works.")


if __name__ == "__main__":
    main()
