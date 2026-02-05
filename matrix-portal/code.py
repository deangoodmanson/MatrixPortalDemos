"""
Matrix Portal M4 USB Frame Receiver
Receives RGB565 frame data via USB serial and displays on 32x64 LED matrix.
Max frame rate: 5 FPS
"""

import time
import board
import displayio
import rgbmatrix
import framebufferio
import usb_cdc
from adafruit_display_text import label
import terminalio
import digitalio
from adafruit_imageload import load
import struct

# Matrix configuration
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 32
MAX_FPS = 5

# Frame data size: 64 * 32 * 2 bytes (RGB565)
FRAME_SIZE = MATRIX_WIDTH * MATRIX_HEIGHT * 2
FRAME_HEADER = b'IMG1'

# Initialize RGB Matrix
displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=MATRIX_WIDTH,
    height=MATRIX_HEIGHT,
    bit_depth=6,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE
)

display = framebufferio.FramebufferDisplay(matrix)

# Create bitmap and group once at startup
# Use a 16-bit bitmap (65536 colors) for RGB565
# Mac sends little-endian RGB565, which we assemble directly in display_frame()
bitmap = displayio.Bitmap(MATRIX_WIDTH, MATRIX_HEIGHT, 65536)
color_converter = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565)

tile_grid = displayio.TileGrid(bitmap, pixel_shader=color_converter)
group = displayio.Group()
group.append(tile_grid)
display.root_group = group

# Setup buttons for self-check
button_up = digitalio.DigitalInOut(board.BUTTON_UP)
button_up.switch_to_input(pull=digitalio.Pull.UP)

button_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
button_down.switch_to_input(pull=digitalio.Pull.UP)


def show_startup_message():
    """Display 'Waiting...' message on matrix."""
    text_group = displayio.Group()

    # Create text labels
    text1 = label.Label(
        terminalio.FONT,
        text="WAITING",
        color=0x00FF00,  # Green
        x=8,
        y=12
    )
    text2 = label.Label(
        terminalio.FONT,
        text="FOR USB",
        color=0x00FF00,
        x=8,
        y=22
    )

    text_group.append(text1)
    text_group.append(text2)
    display.root_group = text_group


def show_kitten():
    """Display kitten image for self-check."""
    print("Self-check: Displaying kitten...")

    # Load the kitten image
    kitten_bitmap, kitten_palette = load("/kitten.bmp")

    # Create a TileGrid to display the image
    kitten_grid = displayio.TileGrid(kitten_bitmap, pixel_shader=kitten_palette)
    kitten_group = displayio.Group()
    kitten_group.append(kitten_grid)

    # Show the image
    display.root_group = kitten_group
    time.sleep(5)
    print("Self-check complete!")


def show_dog():
    """Display dog image for self-check."""
    print("Self-check: Displaying dog...")

    # Load the dog image
    dog_bitmap, dog_palette = load("/dog.bmp")

    # Create a TileGrid to display the image
    dog_grid = displayio.TileGrid(dog_bitmap, pixel_shader=dog_palette)
    dog_group = displayio.Group()
    dog_group.append(dog_grid)

    # Show the image
    display.root_group = dog_group
    time.sleep(5)
    print("Self-check complete!")


def receive_frame(serial):
    """Receive the latest complete frame from the serial buffer.
    Clears old data to reduce latency and ensures synchronization.
    """
    # Check if serial port is available
    if serial is None:
        return None

    # Start reading as soon as we have at least the header
    # This prevents sender timeout by draining the buffer eagerly
    if serial.in_waiting < len(FRAME_HEADER):
        return None

    # Read everything available to find the most recent frame
    all_data = serial.read(serial.in_waiting)
    
    # Search for the header from the end (freshest frame)
    header_idx = all_data.rfind(FRAME_HEADER)
    
    if header_idx == -1:
        return None
        
    start_payload = header_idx + len(FRAME_HEADER)
    
    if len(all_data) >= start_payload + FRAME_SIZE:
        # Full frame is already in our buffer
        return all_data[start_payload : start_payload + FRAME_SIZE]
    else:
        # We found a header but the frame data is still arriving
        payload = bytearray(all_data[start_payload:])
        remaining = FRAME_SIZE - len(payload)
        
        # Wait a short time for the rest
        timeout = 0.1
        start_t = time.monotonic()
        while remaining > 0:
            if time.monotonic() - start_t > timeout:
                print("Sync timeout")
                return None
            if serial.in_waiting > 0:
                chunk = serial.read(min(serial.in_waiting, remaining))
                payload.extend(chunk)
                remaining -= len(chunk)
        return payload


def display_frame(frame_bytes):
    """Update bitmap with RGB565 frame data as efficiently as possible.

    NOTE FOR RASPBERRY PI PORT: CircuitPython's displayio.Bitmap doesn't expose
    a bulk buffer write API, so we must assign pixels individually. When porting
    to Raspberry Pi with regular Python, use numpy or memoryview to write the
    entire frame buffer in one operation for much better performance.
    """
    # Local references for speed
    bm = bitmap
    width = MATRIX_WIDTH

    # Unpack all bytes as 16-bit little-endian integers at once
    # This moves the byte-to-int conversion from Python to C level
    # Format: '<2048H' = 2048 unsigned shorts (16-bit), little-endian
    pixels = struct.unpack('<2048H', frame_bytes)

    # Still need individual assignments (CircuitPython limitation)
    # On Raspberry Pi, replace this with: bitmap_buffer[:] = pixels
    idx = 0
    for y in range(MATRIX_HEIGHT):
        for x in range(width):
            bm[x, y] = pixels[idx]
            idx += 1


def main():
    """Main loop: receive and display frames."""
    print("Matrix Portal M4 USB Frame Receiver")
    print(f"Display: {MATRIX_WIDTH}x{MATRIX_HEIGHT}")
    print(f"Max FPS: {MAX_FPS}")
    print("Waiting for frames...")

    # Show startup message on matrix
    show_startup_message()

    serial = usb_cdc.data

    # Verify serial port is available
    if serial is None:
        print("ERROR: usb_cdc.data is not available!")
        print("Check that boot.py enables data port")
        while True:
            time.sleep(1)

    print(f"USB data port ready: {serial}")
    print(f"Timeout: {serial.timeout}")

    frame_count = 0
    last_display_time = 0
    min_frame_time = 1.0 / MAX_FPS
    receiving_frames = False

    while True:
        # Check for UP button press (show kitten)
        if not button_up.value:  # Button is pressed (active low)
            show_kitten()
            # Return to waiting screen
            if receiving_frames:
                display.root_group = group
            else:
                show_startup_message()
            # Wait for button release
            while not button_up.value:
                time.sleep(0.01)

        # Check for DOWN button press (show dog)
        if not button_down.value:  # Button is pressed (active low)
            show_dog()
            # Return to waiting screen
            if receiving_frames:
                display.root_group = group
            else:
                show_startup_message()
            # Wait for button release
            while not button_down.value:
                time.sleep(0.01)

        current_time = time.monotonic()

        # Check if enough time has passed for next frame
        if current_time - last_display_time < min_frame_time:
            time.sleep(0.01)
            continue

        # Try to receive a frame
        frame_data = receive_frame(serial)

        if frame_data:
            # Switch to bitmap display on first frame
            if not receiving_frames:
                display.root_group = group
                receiving_frames = True
                print("Receiving frames!")

            # Display the frame
            display_frame(frame_data)

            frame_count += 1
            last_display_time = current_time

            if frame_count % 10 == 0:
                print(f"Frames displayed: {frame_count}")
        else:
            # No data available, small delay
            time.sleep(0.01)


if __name__ == "__main__":
    main()
