# Matrix Portal Live Camera Feed Project

## Project Overview
Build a real-time camera feed display system that captures video from a Raspberry Pi camera and displays it on a 32x64 RGB LED matrix via an Adafruit Matrix Portal controller.

## Hardware Components
- **Raspberry Pi 3 or 4**: Main processing unit
- **Adafruit Matrix Portal** (M4 or S3): LED matrix controller
- **32x64 RGB LED Matrix**: HUB75-compatible display (standard kit size)
- **Pi Camera Module or USB Camera**: Video input source
- **USB cable**: Pi to Matrix Portal connection

## Technical Requirements
- **Target Frame Rate**: 24 FPS (achieved)
- **Display Resolution**: 32x64 pixels
- **Color Depth**: 16-bit (RGB565)
- **Connection Method**: USB Serial (CDC) at 4M baud

## Architecture

### High-Level Data Flow
```
Camera → Pi (Capture) → Pi (Process/Resize) → USB → Matrix Portal → LED Display
```

### Component Responsibilities

**Raspberry Pi:**
- Capture camera frames using picamera2 (for Pi Camera) or OpenCV (for USB camera)
- Resize frames from camera resolution to 32x64 pixels
- Convert color space and reduce color depth if needed
- Encode frame data for USB transfer
- Send frames to Matrix Portal via PyUSB

**Matrix Portal:**
- Receive frame data via native USB endpoint
- Parse incoming frame buffer
- Update RGB matrix display
- Handle frame buffering/synchronization

## Implementation Approach

### Pi-Side Software Stack
**Language**: Python 3

**Key Libraries**:
- `picamera2` or `opencv-python`: Camera capture
- `numpy`: Image processing
- `pyserial`: High-speed serial communication

**Processing Pipeline**:
1. Capture frame from camera
2. Resize to 32x64 using fast interpolation (INTER_NEAREST or INTER_LINEAR)
3. Convert to RGB565 (16-bit) or RGB332 (8-bit) format
4. Flatten to byte array
5. Send via USB bulk transfer

### Matrix Portal Software Stack
**Language**: CircuitPython or Arduino

**Key Libraries**:
- `adafruit_matrixportal` or raw `rgbmatrix` libraries
- USB device libraries (built-in)

**Receiving Pipeline**:
1. Set up USB endpoint to receive bulk transfers
2. Read incoming frame buffer
3. Parse bytes into RGB pixel data
4. Update matrix display buffer
5. Refresh display

## Performance Optimizations

### For 10 FPS Target:
- **Per Frame Budget**: 100ms
- **Data Size**: 32 × 64 × 2 bytes (RGB565) = 4,096 bytes per frame
- **USB Transfer Speed**: USB 2.0 (480 Mbps) → easily achievable

### Optimization Strategies:
1. **Color Depth Reduction**: Use RGB565 (16-bit) instead of RGB888 (24-bit)
2. **Frame Skipping**: Drop frames on Pi side if Matrix Portal can't keep up
3. **Compression**: Optional run-length encoding for static regions
4. **Direct Memory Access**: Use numpy arrays for zero-copy operations

## Development Phases

### Phase 1: Basic Camera Capture (Pi)
- Set up camera on Pi
- Capture and display frames locally
- Test resize operations

### Phase 2: USB Communication
- Configure Matrix Portal USB endpoint
- Establish Pi → Matrix Portal USB connection
- Test raw data transfer

### Phase 3: Frame Display
- Send test patterns from Pi
- Display static images on matrix
- Verify color accuracy

### Phase 4: Live Feed Integration
- Connect camera pipeline to USB pipeline
- Implement frame rate control
- Add error handling and reconnection logic

### Phase 5: Optimization
- Measure and improve frame rate
- Reduce latency
- Add features (color correction, brightness control)

## Technical Considerations

### USB Configuration
- Matrix Portal exposes USB device interface when connected to Pi
- Need to identify VID/PID for PyUSB targeting
- May need udev rules on Pi for non-root access

### Color Space
- Camera typically outputs RGB or YUV
- Matrix needs RGB format
- Consider gamma correction for better LED appearance

### Synchronization
- Implement frame pacing on Pi side
- Add frame numbering for dropped frame detection
- Consider double-buffering on Matrix Portal

## Success Criteria
- [ ] Stable 10 FPS display
- [ ] Recognizable camera image on matrix
- [ ] Less than 200ms latency from capture to display
- [ ] No visible tearing or artifacts
- [ ] Graceful handling of disconnections

## Future Enhancements
- Add web interface for remote viewing
- Implement motion detection triggers
- Support multiple camera sources
- Add overlay graphics or text
- Network streaming capability

---

This document provides the foundation for implementation. Start with Phase 1 and iterate through each phase, validating functionality before moving forward.
