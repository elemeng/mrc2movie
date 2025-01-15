### **Introduction**

After collecting your tomography tilt series, you need a quick and convenient way to assess and share the quality of your data. Similarly, after aligning and reconstructing tomograms, you want to present them as movies in presentations or share them with colleagues. However, there are no straightforward tools to directly convert `.mrc` files into movies, making the process cumbersome.

To address this, I created this script to **batch convert `.mrc` files** (such as tilt series and tomograms) into high-quality movies with enhanced contrast. The script offers customizable options to fine-tune the speed, contrast, and playback direction of the movies, making it easy to visualize and share your data. Enjoy exploring the microscopic world with ease! ^v^

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
- **Rich Logging:** Logs detailed information and errors to `mrc2movie.log`.
- **Progress Bars:** Displays progress bars for slice and tomogram processing.
- **Customizable Parameters:** Control frame rate, CLAHE settings, video codec, and more.

---

## **Installation**

1. **Install Python (if not already installed):**
   - Download and install Python from [python.org](https://www.python.org/).
   - Using `conda` or any other virtual environment manager is recommended for better dependency management.

2. **Clone or Download the Script:**
   ```bash
   git clone https://github.com/yourusername/mrc2movie.git
   cd mrc2movie
   ```

3. **(Recommended) Create a Virtual Environment:**
   ```bash
   conda create -n mrc2movie python=3.12
   conda activate mrc2movie
   ```

4. **Install Required Libraries:**
   ```bash
   pip install mrcfile numpy opencv-python tqdm asyncio
   ```

---

## **Usage**

### **Command-Line Interface**

Run the script with the following command:

```bash
python mrc2movie.py input_directory output_directory [--fps FPS] [--clip_limit CLIP_LIMIT] [--tile_grid_size TILE_GRID_SIZE] [--codec CODEC] [--playback {forward,forward-backward}] [--discard_range START END] [--discard_percentage START_PERCENT END_PERCENT]
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
|

### **Examples**

1. **Default Settings:**
   ```bash
   python mrc2movie.py /path/to/mrc_files_dir /path/to/output_dir
   ```
   This converts all `.mrc` files in the `mrc_files_dir` directory into movies saved in the `output_dir` directory, each retaining their original filenames. By default, these movies will have a frame rate of 30 fps. You can adjust the `--fps` parameter to control the playback speed.

2. **Forward-Backward Playback with Discard Percentage:**
   ```bash
   python mrc2movie.py /path/to/mrc_files_directory /path/to/output_directory --fps 25 --clip_limit 1.5 --playback forward-backward --discard_percentage 0.1 0.2
   ```
   These output movies will have a frame rate of 25 fps (slower than the default 30 fps), lower contrast (due to the `clip_limit` of 1.5), and a forward-backward loop playback. The `--discard_percentage 0.1 0.2` option discards 10% of slices from the beginning and 20% from the end of each tomogram. This is useful when the beginning and end of the tomogram are empty or contain artifacts.

3. **Forward-Only Playback with Discard Range:**
   ```bash
   python mrc2movie.py /path/to/mrc_files /path/to/output --fps 10 --clip_limit 1.5 --playback forward --discard_range 10 20
   ```
   This command processes the `.mrc` files, discarding slices 10 to 19 (0-based indexing) and creating forward-only playback movies with a frame rate of 10 fps and a `clip_limit` of 1.5.

---

## **Output**

- **Movies:** Saved in the specified `output_directory` with the same base name as the input `.mrc` files but with a `.avi` extension.
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
