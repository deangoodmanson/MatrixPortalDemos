# LED Portal Utils

Snapshot processing utilities for LED Portal projects.

## Features

- **PNG export**: Export snapshot files as PNG format
- **Block export**: Create larger images with square block effect
- **Circle export**: Create larger images with circular elements on black background

## Installation

This package is designed to be used as a local dependency:

```toml
dependencies = [
    "ledportal-utils @ {path = \"../utils\", editable = true}",
]
```

## Usage

```python
from ledportal_utils import export_png, export_blocks, export_circles

# Export as PNG
export_png("snapshot.bmp")

# Export with block effect (10x scale = 640×320 from 64×32)
export_blocks("snapshot.bmp", scale_factor=10)

# Export with circle effect
export_circles("snapshot.bmp", scale_factor=10, led_size_ratio=0.9)
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
