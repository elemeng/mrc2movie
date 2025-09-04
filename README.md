# MRC2Movie

A high-performance Python toolset to batch convert .mrc files (e.g., tilt series, tomograms) into movies or PNG image slices with enhanced contrast. Perfect for quickly assessing data quality, sharing results, or creating presentations.


## 🚀 Quick Start

### Installation

#### For Users (pip/uv)
```bash
# Install via pip
pip install mrc2movie

# Or via uv (recommended)
uv pip install mrc2movie
```

#### For Developers (uv setup)
```bash
# Clone and setup development environment
git clone https://github.com/your-repo/mrc2movie
cd mrc2movie

# Using uv (recommended for dev)
uv sync                    # Install dependencies
uv run mrc2movie --help    # Run via uv
uv run pytest              # Run tests
```


### Basic Usage
```bash
# Convert MRC files to movies
python mrc2movie.py data/ movies/

# Convert single MRC to PNG sequence
python mrc2png.py sample.mrc output/

# Use presets for common data types
python mrc2movie.py data/ movies/ --preset tilt --speed balanced
```

## 📖 User Guide

### Command-Line Interface

#### mrc2movie.py - Batch Movie Generation

**Basic Syntax:**
```bash
python mrc2movie.py INPUT_DIR OUTPUT_DIR [OPTIONS]
```

**Essential Parameters:**
```bash
# Frame rate optimization
--fps 30          # Built tomograms (default)
--fps 8           # Tilt series (recommended)

# Contrast enhancement
--clip_limit 2    # Built tomograms (default)
--clip_limit 100  # Tilt series (low SNR)

# Output sizing
--output_size 1024  # Default
--output_size 512   # Memory-constrained
--output_size 2048  # High resolution
--output_size 4096  # original for falcon
--output_size 5760  # original for gatan K3
```

**Preset Configurations:**
```bash
# Tomograms (high quality)
python mrc2movie.py data/ output/ --preset tomogram
python mrc2movie.py data/ output/ --preset tomo          # shorthand

# Tilt series (optimized for low SNR)
python mrc2movie.py data/ output/ --preset tiltseries
python mrc2movie.py data/ output/ --preset ts            # shorthand

# Quick preview
python mrc2movie.py data/ output/ --preset quick

# Maximum quality
python mrc2movie.py data/ output/ --preset max_quality
```

**Speed vs Quality Trade-offs:**
```bash
# Fast processing
python mrc2movie.py data/ output/ --speed fast --preset tilt

# Balanced (default)
python mrc2movie.py data/ output/ --speed balanced

# Maximum quality
python mrc2movie.py data/ output/ --speed quality --preset max_quality
```

#### mrc2png.py - PNG Sequence Generation

**Basic Syntax:**
```bash
python mrc2png.py INPUT_FILE OUTPUT_DIR [OPTIONS]
```

**Common Usage:**
```bash
# Basic PNG generation
python mrc2png.py sample.mrc output/

# With custom parameters
python mrc2png.py sample.mrc output/ --clip_limit 50 --output_size 512

# Slice selection
python mrc2png.py sample.mrc output/ --discard_percentage 0.1 0.1
```

### Memory Management

#### Memory Estimation
```bash
# Check memory requirements before processing
python mrc2movie.py data/ output/ --estimate_memory

# Example output:
# File: sample.mrc
#   Shape: (1000, 2048, 2048)
#   Raw size: 8.0 GB
#   Processing memory: 20.0 GB ⚠️
#   WARNING: Large file - may exceed available RAM
```

#### Memory-Conscious Processing
```bash
# For large files (>4GB)
python mrc2movie.py data/ output/ --preset cryo --output_size 512

# Batch processing with memory monitoring
python mrc2movie.py data/ output/ --speed fast --batch-size 2
```

### Advanced Parameters

| Parameter | Description | Built Tomograms | Tilt Series | Cryo Data |
|-----------|-------------|-----------------|-------------|-----------|
| `--fps` | Frame rate | 30 | 2 | 10 |
| `--clip_limit` | CLAHE contrast | 2 | 100 | 5 |
| `--tile_grid_size` | CLAHE tiles | 8 | 16 | 8 |
| `--output_size` | Max dimension | 1024 | 1024 | 512 |
| `--codec` | Video codec | MJPG | MJPG | MJPG |

## 🛠️ Developer Guide

### Architecture Overview

```
mrc2movie/
├── mrc2movie.py      # Main CLI for movie generation
├── mrc2png.py        # CLI for PNG sequence generation
├── mrc_utils.py      # Core processing utilities
```

### API Reference

#### Core Functions

##### `read_tomogram(input_path: str) -> Optional[np.ndarray]`
Memory-efficient MRC file reader with automatic size estimation.

**Parameters:**
- `input_path`: Path to MRC file

**Returns:**
- `np.ndarray`: 3D tomogram data or `None` if error

**Example:**
```python
from mrc_utils import read_tomogram
tomogram = read_tomogram("sample.mrc")
print(f"Loaded: {tomogram.shape}")
```

##### `process_slice(args: Tuple) -> np.ndarray`
Process individual slice with contrast enhancement.

**Parameters:**
- `args`: Tuple of (slice_data, global_min, global_max, clip_limit, tile_grid_size)

**Returns:**
- `np.ndarray`: Enhanced 2D slice

##### `write_slices_to_png(output_dir, basename, slices, ...)`
Write processed slices to PNG files with parallel I/O.

**Parameters:**
- `output_dir`: Output directory path
- `basename`: Base filename for PNGs
- `slices`: 3D array of processed slices
- `output_size`: Maximum dimension for resizing

### Extending the Toolkit

#### Adding New Presets

```python
# In mrc2movie.py, add to preset_params dict
"custom_preset": {
    "fps": 15.0,
    "clip_limit": 20.0,
    "output_size": 768
}
```

#### Custom Processing Pipeline

```python
from mrc_utils import read_tomogram, process_slice, write_slices_to_png
import numpy as np

# Custom processing pipeline
def custom_pipeline(input_path, output_path):
    tomogram = read_tomogram(input_path)
    if tomogram is None:
        return
    
    # Custom processing
    processed = []
    global_min, global_max = tomogram.min(), tomogram.max()
    
    for slice_data in tomogram:
        enhanced = process_slice((slice_data, global_min, global_max, 10.0, 8))
        processed.append(enhanced)
    
    # Save results
    write_slices_to_png(output_path, "custom", np.array(processed))
```

### Performance Tuning

#### Profiling Mode
```bash
# Enable detailed timing for optimization
python mrc2movie.py data/ output/ --profile --preset tilt

# Output includes:
# - Memory usage per file
# - Processing time per slice
# - I/O performance metrics
```

#### Memory Optimization
```python
# For memory-constrained environments
from mrc_utils import estimate_memory_usage

# Check before processing
estimate_memory_usage("large_file.mrc")
# File: large_file.mrc
#   Shape: (2000, 4096, 4096)
#   Processing memory: 160.0 GB ⚠️
```

### Error Handling

#### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| `MemoryError` | Use `--output_size 512` or `--speed fast` |
| `cv2.error` | Check codec support, try `--codec MJPG` |
| `No MRC files` | Verify file extensions (.mrc, .st) |
| `Permission denied` | Check output directory permissions |

#### Debugging
```bash
# Verbose logging
python mrc2movie.py data/ output/ --verbose

# Memory debugging
python -m memory_profiler mrc2movie.py data/ output/
```


## 🔬 Experimental Features

### Parameter Sweeps
```bash
# Automated parameter optimization
for clip in 1 5 10 50 100; do
    python mrc2movie.py data/ output/ --clip_limit $clip --preset tilt
done
```

### Quality Assessment
```bash
# Compare different presets
python mrc2movie.py data/ output/ --preset built --speed quality
python mrc2movie.py data/ output/ --preset built --speed fast
diff output/ output_fast/
```

## 📝 Contributing

### Development Setup

#### Using uv (Recommended)
```bash
git clone https://github.com/your-repo/mrc2movie
cd mrc2movie

# Install and activate virtual environment
uv sync
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run tools directly
uv run mrc2movie data/ output/ --preset tilt
uv run mrc2png sample.mrc output/

# Development commands
uv run pytest tests/
uv run black .
uv run ruff check .
```

#### Using pip
```bash
git clone https://github.com/your-repo/mrc2movie
cd mrc2movie
pip install -e ".[dev]"
pytest tests/
```

### Adding Tests
```python
# tests/test_mrc_utils.py
def test_process_slice():
    slice_data = np.random.rand(512, 512)
    result = process_slice((slice_data, 0, 1, 2.0, 8))
    assert result.shape == (512, 512)
    assert result.dtype == np.uint8
```

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/mrc2movie/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/mrc2movie/discussions)
