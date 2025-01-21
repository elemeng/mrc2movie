### **Introduction**

After collecting tomography tilt series data, researchers need an efficient method to evaluate and share data quality. Following tomogram alignment and reconstruction, presenting results as movies is essential for both presentations and collaboration. However, the lack of direct tools for converting **`.mrc`** files to movies creates unnecessary complexity in the workflow.

To address this, I created this toolset to **batch convert `.mrc` files** (such as tilt series and tomograms) into high-quality movies with enhanced contrast. The toolset offers customizable options to fine-tune the speed, contrast, and playback direction of the movies, making it easy to visualize and share your data. Enjoy exploring the microscopic world with ease! ^v^

You can also use this to save the tomogram tilt series or reconstructed tomograms into **`pngs`**.

---

# MRC to Movie/PNG Converter

A high-performance Python toolset to batch convert `.mrc` files (e.g., tilt series, tomograms) into movies or PNG image slices with enhanced contrast. Perfect for quickly assessing data quality, sharing results, or creating presentations.

---

## **Features**

- **Batch Processing:** Convert multiple `.mrc` files in a directory into movies or PNG slices.
- **Contrast Enhancement:** Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) for balanced contrast.
- **Global Normalization:** Normalize slices using global min/max values for consistent contrast.
- **Playback Direction:** Choose between **forward-only** or **forward-backward** playback (for movies).
- **Discard Slices:** Discard a range of slices or a percentage of slices from the beginning and end.
- **PNG Output:** Save processed slices as PNG images.
- **Rich Logging:** Logs detailed information and errors to `mrc2movie.log` or `mrc2png.log`.
- **Progress Bars:** Displays progress bars for slice and tomogram processing.
- **Customizable Parameters:** Control frame rate, CLAHE settings, video codec, and more.

---

## **Installation**

1. **Install Python (if not already installed):**
   - Download and install Python 3.12+ from [python.org](https://www.python.org/)

2. **Clone the Repository:**
   ```bash
   git clone https://github.com/elemeng/mrc-converter.git
   cd mrc-converter
   ```

3. **Install:**
   ```bash
   # Install UV if not already installed
   pip install uv

   # Create virtual environment and install dependencies
   uv sync
   uv pip install -e .
   ```

4. **Verify Installation:**
   ```bash
   mrc2movie --version
   mrc2png --version
   ```

---

## **Usage**

### **1. Convert MRC to PNG**

Use the `mrc2png.py` script to convert an MRC file into PNG image slices. This is useful for visualizing individual slices or preparing data for further analysis.

#### Command
```bash
python mrc2png.py input.mrc output_dir [options]
```

#### Options
| Argument                | Description                                                                 | Default Value         |
|-------------------------|-----------------------------------------------------------------------------|-----------------------|
| `input.mrc`             | Path to the input `.mrc` file.                                              | Required              |
| `output_dir`            | Directory to save output PNG files.                                         | Required              |
| `--discard_range`       | Discard slices from `START` to `END` (0-based indexing).                    | None                  |
| `--discard_percentage`  | Discard `START_PERCENT` from the beginning and `END_PERCENT` from the end.  | None                  |
| `--output_size`         | Resize output images to a maximum dimension of `SIZE`.                      | 1024                  |

#### Example
```bash
python mrc2png.py example.mrc output_images --discard_percentage 0.1 0.1 --output_size 512
```

This command:
- Converts `example.mrc` into PNG images.
- Discards 10% of slices from the beginning and end.
- Resizes the output images to a maximum dimension of 512 pixels.
- Saves the PNG files in the `output_images` directory.

---

### **2. Convert MRC to Movie**

Use the `mrc2movie.py` script to convert an MRC file into a video. This is ideal for creating animations of tomographic data.

#### Command
```bash
python mrc2movie.py input_directory output_directory [options]
```

#### Options
| Argument                | Description                                                                 | Default Value         |
|-------------------------|-----------------------------------------------------------------------------|-----------------------|
| `input_directory`       | Directory containing `.mrc` files.                                          | Required              |
| `output_directory`      | Directory to save output movies.                                            | Required              |
| `--fps`                 | Frame rate for the output movie. For built tomogram, 20~30 is good. For tilt series, 1~2 is good.                                           | `30.0`                |
| `--clip_limit`          | CLAHE clip limit for contrast enhancement. For tilt series, you try 30~1000 or more large number to enhance contrast.                                | `2.0`                 |
| `--tile_grid_size`      | CLAHE tile grid size (controls local contrast granularity).                 | `8`                   |
| `--codec`               | Video codec (e.g., `MJPG`, `XVID`, `DIVX`).                                | `MJPG`                |
| `--playback`            | Playback direction: `forward` or `forward-backward`.                       | `forward-backward`    |
| `--discard_range`       | Discard slices from `START` to `END` (0-based indexing).                    | None                  |
| `--discard_percentage`  | Discard `START_PERCENT` from the beginning and `END_PERCENT` from the end.  | None                  |
| `--png`                 | Save processed slices as PNG files in addition to video output.            | False                 |
| `--output_size`         | Resize output video and images to a maximum dimension of `SIZE`.           | 1024                  |

#### Example
```bash
python mrc2movie.py input_mrcs output_videos --fps 25 --clip_limit 3.0 --png --output_size 768
```

This command:
- Converts all MRC files in the `input_mrcs` directory into videos.
- Sets the frame rate to 25 fps.
- Enhances contrast with a CLAHE clip limit of 3.0.
- Saves intermediate PNG files alongside the videos.
- Resizes the output to a maximum dimension of 768 pixels.
- Saves the videos in the `output_videos` directory.

---

## **Output**

- **Movies:** Saved in the specified `output_directory` with the same base name as the input `.mrc` files but with a `.avi` extension.
- **PNG Slices:** Saved in `{basename}_slices` directories when using the `--png` flag.
- **Logs:** Detailed logs are written to `mrc2movie.log` or `mrc2png.log`.

---

## **Development**

### **Running Tests**
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=mrc2movie --cov-report=html
```

### **Code Quality Checks**
```bash
# Run pre-commit checks on all files
pre-commit run --all-files

# Run type checking
mypy src/

# Run linting
ruff check src/
```

### **Building Documentation**
```bash
# Generate API documentation
pdoc --html --output-dir docs src/
```

## **Contributing**

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a new Pull Request

Please ensure your code:
- Follows PEP 8 style guidelines
- Includes type hints
- Has corresponding tests
- Updates documentation as needed

## **Performance Tips**

1. **Hardware:**
   - Use a system with multiple CPU cores and fast storage (SSD/NVMe) for optimal performance.

2. **CLAHE Parameters:**
   - Adjust `clip_limit` and `tile_grid_size` to balance contrast enhancement and processing speed.

3. **Profiling:**
   - Use `cProfile` to identify and optimize bottlenecks:
     ```bash
     python -m cProfile -s cumtime mrc2movie.py /path/to/mrc_files /path/to/output
     ```

---

## **License**

This project is licensed under the MIT License. 

---

Enjoy visualizing your tomograms with ease! 🎥✨
