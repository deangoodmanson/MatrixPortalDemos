#!/usr/bin/env python3
"""
Utility to list available USB serial devices.
Helps identify the Matrix Portal M4 serial port.
"""

import serial.tools.list_ports

def main():
    print("Available USB Serial Devices:")
    print("-" * 60)

    ports = serial.tools.list_ports.comports()

    if not ports:
        print("No USB serial devices found.")
        return

    for i, port in enumerate(ports, 1):
        print(f"\n{i}. {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Manufacturer: {port.manufacturer}")
        if port.vid and port.pid:
            print(f"   VID:PID: {port.vid:04x}:{port.pid:04x}")

        # Highlight if it looks like CircuitPython
        if "CircuitPython" in port.description:
            if "data" in port.description.lower():
                print(f"   >>> This is the Matrix Portal M4 DATA port <<<")
            else:
                print(f"   (CircuitPython console port)")

    print("-" * 60)


if __name__ == "__main__":
    main()
