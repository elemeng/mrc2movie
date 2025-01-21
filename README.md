# MRC to Movie/PNG Converter

A high-performance Python toolset to batch convert `.mrc` files (e.g., tilt series, tomograms) into movies or PNG image slices with enhanced contrast. Perfect for quickly assessing data quality, sharing results, or creating presentations.

---

## Table of Contents
- [MRC to Movie/PNG Converter](#mrc-to-moviepng-converter)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
    - [Core Functionality](#core-functionality)
    - [Advanced Features](#advanced-features)
    - [Quality of Life](#quality-of-life)
  - [Installation](#installation)
  - [Usage](#usage)
    - [1. Convert MRC to PNG](#1-convert-mrc-to-png)
      - [Command](#command)
      - [Options](#options)
      - [Example](#example)
    - [2. Convert MRC to Movie](#2-convert-mrc-to-movie)
      - [Command](#command-1)
      - [Options](#options-1)
      - [Example](#example-1)
    - [Building Documentation](#building-documentation)
  - [Contributing](#contributing)
  - [Performance Tips](#performance-tips)
  - [License](#license)

---

## Features

### Core Functionality
- **Batch Processing:** Convert multiple `.mrc` files in a directory into movies or PNG slices
- **Contrast Enhancement:** Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) for balanced contrast
- **Global Normalization:** Normalize slices using global min/max values for consistent contrast

### Advanced Features
- **Frame Resizing:** Automatically resizes frames to match output dimensions, fixing issues with small MRC files
- **Playback Direction:** Choose between **forward-only** or **forward-backward** playback (for movies)
- **Discard Slices:** Discard a range of slices or a percentage of slices from the beginning and end
- **PNG Output:** Save processed slices as PNG images

### Quality of Life
- **Rich Logging:** Detailed information and errors logged to `mrc2movie.log` or `mrc2png.log`
- **Progress Bars:** Visual feedback for slice and tomogram processing
- **Customizable Parameters:** Control frame rate, CLAHE settings, video codec, and more

---

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/elemeng/mrc-converter.git
   cd mrc-converter
   ```

2. **Install:**
   ```bash
   # Install UV if not already installed
   pip install uv

   # Create virtual environment and install dependencies
   uv sync
   uv pip install -e .
   ```

3. **Verify Installation:**
   ```bash
   mrc2movie --version
   mrc2png --version
   ```

---

## Usage

### 1. Convert MRC to PNG

Use the `mrc2png.py` script to convert an MRC file into PNG image slices. This is useful for visualizing individual slices or preparing data for further analysis.

#### Command
```bash
python mrc2png.py input.mrc output_dir [options]
```

#### Options
| Argument               | Description                                                                | Default Value |
| ---------------------- | -------------------------------------------------------------------------- | ------------- |
| `input.mrc`            | Path to the input `.mrc` file.                                             | Required      |
| `output_dir`           | Directory to save output PNG files.                                        | Required      |
| `--discard_range`      | Discard slices from `START` to `END` (0-based indexing).                   | None          |
| `--discard_percentage` | Discard `START_PERCENT` from the beginning and `END_PERCENT` from the end. | None          |
| `--output_size`        | Resize output images to a maximum dimension of `SIZE`.                     | 1024          |

#### Example
```bash
python mrc2png.py example.mrc output_images --discard_percentage 0.1 0.1 --output_size 512
```

---

### 2. Convert MRC to Movie

Use the `mrc2movie.py` script to convert an MRC file into a video. This is ideal for creating animations of tomographic data.

#### Command
```bash
python mrc2movie.py input_directory output_directory [options]
```

#### Options
| Argument               | Description                                                                                                           | Default Value      |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `input_directory`      | Directory containing `.mrc` files.                                                                                    | Required           |
| `output_directory`     | Directory to save output movies.                                                                                      | Required           |
| `--fps`                | Frame rate for the output movie. For built tomogram, 20~30 is good. For tilt series, 1~2 is good.                     | `30.0`             |
| `--clip_limit`         | CLAHE clip limit for contrast enhancement. For tilt series, you try 30~1000 or more large number to enhance contrast. | `2.0`              |
| `--tile_grid_size`     | CLAHE tile grid size (controls local contrast granularity).                                                           | `8`                |
| `--codec`              | Video codec (e.g., `MJPG`, `XVID`, `DIVX`).                                                                           | `MJPG`             |
| `--playback`           | Playback direction: `forward` or `forward-backward`.                                                                  | `forward-backward` |
| `--discard_range`      | Discard slices from `START` to `END` (0-based indexing).                                                              | None               |
| `--discard_percentage` | Discard `START_PERCENT` from the beginning and `END_PERCENT` from the end.                                            | None               |
| `--png`                | Save processed slices as PNG files in addition to video output.                                                       | False              |
| `--output_size`        | Resize output video and images to a maximum dimension of `SIZE`.                                                      | 1024               |

#### Example
```bash
python mrc2movie.py input_mrcs output_videos --fps 25 --clip_limit 3.0 --png --output_size 768
```

### Building Documentation
```bash
# Generate API documentation
pdoc --html --output-dir docs src/
```

---

## Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a new Pull Request

Please ensure your code:
- Follows PEP 8 style guidelines
- Includes type hints
- Updates documentation as needed

---

## Performance Tips


1. **CLAHE Parameters:**
   - Adjust `clip_limit` and `tile_grid_size` to balance contrast enhancement and processing speed.

2. **Profiling:**
   - Use `cProfile` to identify and optimize bottlenecks:
     ```bash
     python -m cProfile -s cumtime mrc2movie.py /path/to/mrc_files /path/to/output
     ```

---

## License

This project is licensed under the MIT License. 

---

Enjoy visualizing your tomograms with ease! 🎥✨
