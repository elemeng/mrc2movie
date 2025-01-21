### **Introduction**

After collecting tomography tilt series data, researchers need an efficient method to evaluate and share data quality. Following tomogram alignment and reconstruction, presenting results as movies is essential for both presentations and collaboration. However, the lack of direct tools for converting **`.mrc`** files to movies creates unnecessary complexity in the workflow.

To address this, I created this script to **batch convert `.mrc` files** (such as tilt series and tomograms) into high-quality movies with enhanced contrast. The script offers customizable options to fine-tune the speed, contrast, and playback direction of the movies, making it easy to visualize and share your data. Enjoy exploring the microscopic world with ease! ^v^

You can also use this to save the tomogram tilt seriers or reconstructured tomograms into **`pngs`**.

---

# MRC to Movie Converter

A high-performance Python script to batch convert `.mrc` files (e.g., tilt series, tomograms) into movies with enhanced contrast. Perfect for quickly assessing data quality, sharing results, or creating presentations.

---

## **Features**

- **Batch Processing:** Convert multiple `.mrc` files in a directory into movies.
- **Contrast Enhancement:** Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) for balanced contrast.
- **Global Normalization:** Normalize slices using global min/max values for consistent contrast.
- **Playback Direction:** Choose between **forward-only** or **forward-backward** playback.
- **Discard Slices:** Discard a range of slices or a percentage of slices from the beginning and end.
- **PNG Output:** Optionally save processed slices as PNG images.
- **Rich Logging:** Logs detailed information and errors to `mrc2movie.log`.
- **Progress Bars:** Displays progress bars for slice and tomogram processing.
- **Customizable Parameters:** Control frame rate, CLAHE settings, video codec, and more.

---

## **Installation**

1. **Install Python (if not already installed):**
   - Download and install Python from [python.org](https://www.python.org/).

2. **Clone or Download the Script:**
   ```bash
   git clone https://github.com/elemeng/mrc2movie.git
   cd mrc2movie
   ```

3. **(Recommended) Using uv to set up Virtual Environment:**
   ```bash
   pip install uv
   uv sync
   ```
   **Nice, everything is prepared for you to run this script.**
   Optionally, You can also use conda to set up an Virtual Environment

---

## **Usage**

### **Command-Line Interface**

Run the script with the following command:

```bash
python mrc2movie.py input_directory output_directory [--fps FPS] [--clip_limit CLIP_LIMIT] [--tile_grid_size TILE_GRID_SIZE] [--codec CODEC] [--playback {forward,forward-backward}] [--discard_range START END] [--discard_percentage START_PERCENT END_PERCENT] [--png]
```

### **Arguments**

| Argument                | Description                                                                 | Default Value         |
|-------------------------|-----------------------------------------------------------------------------|-----------------------|
| `input_directory`       | Directory containing `.mrc` files.                                          | Required              |
| `output_directory`      | Directory to save output movies.                                            | Required              |
| `--fps`                 | Frame rate for the output movie.                                            | `30.0`                |
| `--clip_limit`          | CLAHE clip limit for contrast enhancement.                                  | `2.0`                 |
| `--tile_grid_size`      | CLAHE tile grid size (controls local contrast granularity).                 | `8`                   |
| `--codec`               | Video codec (e.g., `MJPG`, `XVID`, `DIVX`).                                | `MJPG`                |
| `--playback`            | Playback direction: `forward` or `forward-backward`.                       | `forward-backward`    |
| `--discard_range`       | Discard slices from START to END (0-based indexing).                        | None                  |
| `--discard_percentage`  | Discard START_PERCENT from the beginning and END_PERCENT from the end.      | None                  |
| `--png`                 | Save processed slices as PNG files in addition to video output.            | False                 |

### **PNG Output**

When using the `--png` flag, the script will save individual slices as PNG images alongside the video output. This is useful for detailed inspection of specific slices or for creating custom visualizations.

**Output Structure:**
- For each input `.mrc` file, a new directory will be created with the naming pattern: `{input_basename}_slices`
- Each slice will be saved as a PNG file with 4-digit sequential numbering (e.g., `input_0000.png`, `input_0001.png`, etc.)
- The PNG files will have the same contrast enhancement and normalization as the video output
- The directory structure will be preserved relative to the input files

**Example Output:**
```
output_directory/
├── input1.avi
├── input1_slices/
│   ├── input1_0000.png
│   ├── input1_0001.png
│   └── ...
└── subdir/
    ├── input2.avi
    └── input2_slices/
        ├── input2_0000.png
        ├── input2_0001.png
        └── ...
```

### **Examples**

1. **Basic Conversion with both movie and PNG Output:**
   ```bash
   python mrc2movie.py /path/to/mrc_files /path/to/output --png
   ```
   Converts all `.mrc` files while saving both movies and individual PNG slices.

2. **Custom Frame Rate and Contrast movie (with PNG Output):**
   ```bash
   python mrc2movie.py /path/to/mrc_files /path/to/output --fps 15 --clip_limit 3.0 --png
   ```
   Creates movies at 15 FPS with higher contrast (clip_limit=3.0) while saving PNG slices.

3. **Selective Slice Processing movie (with PNG Output):**
   ```bash
   python mrc2movie.py /path/to/mrc_files /path/to/output --discard_range 10 20 --png
   ```
   Processes slices while skipping slices 10-19 (0-based indexing) and saves both movies and PNGs.

4. **Percentage-based Slice Discard movie (with PNG Output):**
   ```bash
   python mrc2movie.py /path/to/mrc_files /path/to/output --discard_percentage 0.1 0.2 --png
   ```
   Discards 10% of slices from the start and 20% from the end while saving PNGs of the remaining slices.

---

## **Output**

- **Movies:** Saved in the specified `output_directory` with the same base name as the input `.mrc` files but with a `.avi` extension.
- **PNG Slices:** Saved in `{basename}_slices` directories when using the `--png` flag.
- **Logs:** Detailed logs are written to `mrc2movie.log`.

---

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
