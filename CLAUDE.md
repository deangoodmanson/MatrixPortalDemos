# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a real-time camera feed display system that captures video from a Raspberry Pi camera and displays it on a 32x64 RGB LED matrix via an Adafruit Matrix Portal M4 controller.

**Target Performance**: 10 FPS at 32x64 resolution with <200ms latency

## Development Philosophy

**This is a demonstration and showcase project, not a production product.**

- **Prioritize simplicity and readability** over advanced features or optimization
- **Use Python for Raspberry Pi code** - it's preferred for this project
- **Do NOT over-engineer**: Avoid abstractions, frameworks, or features beyond immediate needs
- **Keep it straightforward**: Simple, linear code is better than clever or complex solutions
- **No unnecessary error handling**: Handle only realistic failure cases
- **No premature optimization**: Get it working first, optimize only if needed to hit 10 FPS target

## System Architecture

The system consists of two separate software components that communicate via USB:

### Raspberry Pi Component (Python)
- Captures frames from Pi Camera or USB camera
- Processes and resizes to 32x64 pixels
- Converts to RGB565 (16-bit) or RGB332 (8-bit) format
- Sends frames via PyUSB raw USB transfers (not serial)

**Key Libraries**: `picamera2` or `opencv-python`, `numpy`, `pyusb`, optionally `PIL/Pillow`

### Matrix Portal M4 Component (CircuitPython)
- Receives frame data via native USB endpoint
- Parses incoming frame buffer
- Updates the 32x64 RGB LED matrix display
- Handles frame buffering and synchronization

**Key Libraries**: `adafruit_matrixportal` or raw `rgbmatrix` libraries, USB device libraries

### Data Flow
```
Camera → Pi (Capture) → Pi (Resize/Process) → USB Bulk Transfer → Matrix Portal → LED Matrix
```

## Critical Technical Details

### Frame Format
- **Resolution**: 32x64 pixels (2,048 pixels)
- **Color Format**: RGB565 (16-bit, 4,096 bytes/frame) or RGB332 (8-bit, 2,048 bytes/frame)
- **Frame Budget**: 100ms per frame for 10 FPS target

### USB Communication
- Uses raw USB bulk transfers (not USB serial)
- Matrix Portal exposes USB device interface
- May require udev rules on Pi for non-root access
- Need to identify VID/PID for PyUSB device targeting

### Performance Considerations
- Use fast interpolation (INTER_NEAREST or INTER_LINEAR) for resizing
- Leverage numpy arrays for zero-copy operations
- Implement frame pacing on Pi side
- Consider frame numbering to detect dropped frames
- Apply gamma correction for better LED appearance

## Development Phase Order

When implementing this project, follow this sequence:

1. **Basic Camera Capture (Pi)**: Set up camera, capture frames, test resize operations
2. **USB Communication**: Configure Matrix Portal USB endpoint, establish connection, test data transfer
3. **Frame Display**: Send test patterns, display static images, verify color accuracy
4. **Live Feed Integration**: Connect pipelines, implement frame rate control, add error handling
5. **Optimization**: Measure performance, reduce latency, add features

## Hardware Setup

- **Raspberry Pi 3 or 4** with camera module or USB camera
- **Adafruit Matrix Portal M4** connected via USB to Pi
- **32x64 RGB LED Matrix** (HUB75-compatible) connected to Matrix Portal M4

## Color Space Handling

- Camera outputs RGB or YUV; matrix needs RGB
- Convert to RGB565 to reduce bandwidth: 5 bits red, 6 bits green, 5 bits blue
- Alternative RGB332: 3 bits red, 3 bits green, 2 bits blue for lower bandwidth
- Consider gamma correction for LED display characteristics
