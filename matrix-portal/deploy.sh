#!/bin/bash
# deploy.sh — copy firmware to CIRCUITPY and stamp the build hash
set -e

DEST="/Volumes/CIRCUITPY"

if [ ! -d "$DEST" ]; then
    echo "ERROR: $DEST not mounted. Plug in the Matrix Portal and try again."
    exit 1
fi

BUILD=$(git rev-parse --short HEAD)
echo "Deploying build $BUILD to $DEST..."

# Write version file so the device can report what's running
echo "BUILD = \"$BUILD\"" > "$DEST/version.py"

# Copy all firmware files
cp code.py          "$DEST/code.py"
cp boot.py          "$DEST/boot.py"
cp settings.toml    "$DEST/settings.toml"
cp image_display.py "$DEST/image_display.py"
cp silly_bird.py    "$DEST/silly_bird.py"

echo "Done. Device will reboot with build $BUILD."
echo "Check serial console for: Matrix Portal M4 — mode: both  build: $BUILD"
