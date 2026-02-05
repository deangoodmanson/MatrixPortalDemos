#!/usr/bin/env python3
"""
Check camera availability and permissions on macOS.
"""

import cv2

def main():
    print("Checking camera availability...")
    print()

    # Try to open camera 0
    print("Attempting to open camera 0...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ FAILED: Cannot open camera 0")
        print()
        print("Common causes:")
        print("1. Camera permissions not granted to Terminal")
        print("   → Open System Settings → Privacy & Security → Camera")
        print("   → Enable camera for your terminal app")
        print()
        print("2. Camera is in use by another application")
        print("   → Close Photo Booth, Zoom, etc.")
        print()
        print("3. No camera connected")
        print("   → Connect a USB webcam or check built-in camera")
        return

    print("✓ Camera 0 opened successfully")

    # Try to read a frame
    print("Attempting to capture a frame...")
    ret, frame = cap.read()

    if not ret:
        print("❌ FAILED: Cannot capture frame")
        cap.release()
        return

    print(f"✓ Frame captured: {frame.shape}")
    print()
    print("Camera is working correctly!")

    cap.release()


if __name__ == "__main__":
    main()
