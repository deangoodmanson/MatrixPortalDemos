#!/usr/bin/env python3
"""
Test which port is the data port by sending test patterns to both.
"""

import serial
import serial.tools.list_ports
import time
import numpy as np
from config import MATRIX_WIDTH, MATRIX_HEIGHT

def create_test_pattern(color_value):
    """Create a solid color test pattern."""
    # Create RGB565 value (5-6-5 bits)
    rgb565 = np.full((MATRIX_HEIGHT, MATRIX_WIDTH), color_value, dtype=np.uint16)
    return rgb565.astype('<u2').tobytes()

def find_matrix_ports():
    """Find all Matrix Portal ports."""
    ports = serial.tools.list_ports.comports()
    matrix_ports = []
    for port in ports:
        if "CircuitPython" in port.description or "Matrix Portal" in port.description:
            matrix_ports.append(port.device)
    return sorted(matrix_ports)

def test_port(port_path, color_name, color_value):
    """Send test pattern to a specific port."""
    print(f"\n{'='*60}")
    print(f"Testing {port_path} with {color_name} pattern")
    print(f"{'='*60}")
    print("Watch the Matrix Portal - you should see the display change!")
    print("Sending pattern for 3 seconds...")

    try:
        ser = serial.Serial(port_path, baudrate=115200, timeout=0.1)
        test_pattern = create_test_pattern(color_value)

        # Send pattern repeatedly for 3 seconds
        for i in range(30):
            bytes_written = ser.write(test_pattern)
            ser.flush()
            if i == 0:
                print(f"First write: {bytes_written} bytes")
            time.sleep(0.1)

        print(f"Sent pattern to {port_path}")
        ser.close()

        input("\nPress Enter to continue to next test...")

    except Exception as e:
        print(f"Error with {port_path}: {e}")

if __name__ == "__main__":
    ports = find_matrix_ports()

    if len(ports) != 2:
        print(f"Expected 2 ports, found {len(ports)}")
        for p in ports:
            print(f"  {p}")
        exit(1)

    print("Matrix Portal Ports:")
    print(f"  Port 1: {ports[0]}")
    print(f"  Port 2: {ports[1]}")
    print("\nWe'll send different colored patterns to each port.")
    print("Watch the LED matrix to see which port works!\n")

    # Test first port with RED
    test_port(ports[0], "RED", 0xF800)

    # Test second port with BLUE
    test_port(ports[1], "BLUE", 0x001F)

    print("\n" + "="*60)
    print("Test complete! Which port showed a color on the matrix?")
    print("="*60)
