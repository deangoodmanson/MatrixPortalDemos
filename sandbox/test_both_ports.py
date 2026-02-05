#!/usr/bin/env python3
"""
Test script to identify which port is the data port.
Sends test data to both ports and checks which one works.
"""

import serial
import serial.tools.list_ports
import time

def find_matrix_ports():
    """Find all Matrix Portal ports."""
    ports = serial.tools.list_ports.comports()
    matrix_ports = []

    for port in ports:
        if "CircuitPython" in port.description or "Matrix Portal" in port.description:
            matrix_ports.append(port.device)

    return sorted(matrix_ports)

def test_port(port_path):
    """Try to send data to a port."""
    print(f"\nTesting {port_path}...")
    try:
        ser = serial.Serial(port_path, baudrate=115200, timeout=0.1)
        test_data = b"TEST" * 1024  # 4KB test data
        bytes_written = ser.write(test_data)
        print(f"  Wrote {bytes_written} bytes")
        ser.close()
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

if __name__ == "__main__":
    ports = find_matrix_ports()

    if len(ports) < 2:
        print(f"Found {len(ports)} port(s), expected 2")
        for p in ports:
            print(f"  {p}")
    else:
        print(f"Found Matrix Portal ports:")
        for p in ports:
            print(f"  {p}")

        print("\nTesting both ports...")
        print("(The data port should accept writes without errors)")
        print("(The console port might also work but is for REPL)")

        for port in ports:
            test_port(port)
