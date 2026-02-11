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

### Basic Usage

```python
from ledportal_utils import export_png, export_blocks, export_circles

# Export as PNG
export_png("snapshot.bmp")  # → snapshot.png

# Export with block effect (10x scale = 640×320 from 64×32)
export_blocks("snapshot.bmp", scale_factor=10)  # → snapshot_blocks.png

# Export with circle effect
export_circles("snapshot.bmp", scale_factor=10, led_size_ratio=0.9)  # → snapshot_circles.png
```

### Batch Processing Example

Process all snapshots in a directory:

```python
from ledportal_utils import export_blocks, export_circles
from pathlib import Path

# Find all snapshot BMP files
snapshots = list(Path('.').glob('snapshot_*.bmp'))

print(f"Found {len(snapshots)} snapshot files\n")

for snapshot in sorted(snapshots):
    print(f"Processing: {snapshot.name}")

    # Create blocks version
    blocks_file = export_blocks(snapshot, scale_factor=10)
    blocks_size = blocks_file.stat().st_size / 1024
    print(f"  ✓ Blocks:  {blocks_file.name} ({blocks_size:.1f} KB)")

    # Create circles version
    circles_file = export_circles(snapshot, scale_factor=10, led_size_ratio=0.9)
    circles_size = circles_file.stat().st_size / 1024
    print(f"  ✓ Circles: {circles_file.name} ({circles_size:.1f} KB)")
    print()
```

### Custom Output Paths

```python
from ledportal_utils import export_blocks, export_circles

# Specify custom output paths
export_blocks("snapshot.bmp", output_path="output/large_blocks.png", scale_factor=20)
export_circles("snapshot.bmp", output_path="output/led_display.png", scale_factor=15)
```

### Adjusting Circle Size

```python
from ledportal_utils import export_circles

# Larger circles (95% of cell size, less gap)
export_circles("snapshot.bmp", led_size_ratio=0.95)

# Smaller circles (80% of cell size, more gap)
export_circles("snapshot.bmp", led_size_ratio=0.80)

# Custom background color (dark blue instead of black)
export_circles("snapshot.bmp", background_color=(0, 0, 20))
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
