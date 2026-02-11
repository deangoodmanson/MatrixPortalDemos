# LED Portal Utils

Snapshot processing utilities for LED Portal projects.

## Features

- **BMP to PNG conversion**: Convert snapshot BMP files to PNG format
- **Pixelated upscaling**: Create larger images with square LED pixel effect
- **LED circle upscaling**: Create larger images with circular LED "bulbs" on black background

## Installation

This package is designed to be used as a local dependency:

```toml
dependencies = [
    "ledportal-utils @ {path = \"../utils\", editable = true}",
]
```

## Usage

```python
from ledportal_utils import bmp_to_png, upscale_pixelated, upscale_led_circles

# Convert BMP to PNG
bmp_to_png("snapshot.bmp")

# Create pixelated version (10x scale = 640×320 from 64×32)
upscale_pixelated("snapshot.bmp", scale_factor=10)

# Create LED circle version
upscale_led_circles("snapshot.bmp", scale_factor=10, led_size_ratio=0.9)
```

## Development

```bash
# Install dependencies
uv sync

# Run linting
uv run ruff check src/
uv run ruff format src/

# Run type checking
uv run ty check src/
```
