# mrc2movie

Convert MRC tomograms into video with optional particle overlay.

## Quick start

```bash
pip install mrcfile numpy opencv-python tqdm

# Basic
python mrc2movie.py -m tomogram.mrc -o movie.avi

# With particles
python mrc2movie.py -m tomogram.mrc -p particles.txt -o movie.avi
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv run mrc2movie.py -m tomogram.mrc -o movie.avi
```

## Particle input

Both IMOD binary files and text files are supported:

**IMOD** (`.mod`):  `-i model.mod` — automatically parsed, no extra dependencies.

**Text file**:  `-p particles.txt` — one `x y z` per line:

```txt
720  511  0      # x  y  z
100  200  10
500  800  15
```

Comma-separated also works: `720,511,0`. Lines starting with `#` and blank lines are skipped.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `-m` / `--mrc` | (required) | MRC input file |
| `-i` / `--imod` | — | IMOD particle file (.mod) |
| `-p` / `--particles` | — | Particle coordinates file (txt) |
| `-o` / `--output` | `output.avi` | Output video |
| `-f` / `--fps` | `10` | Frame rate |
| `-b` / `--bin` | `1` | Downsample factor (2 = half size) |
| `--start` | `0` | First slice index |
| `--end` | `0` | Last slice index (0 = last) |
| `--clip-limit` | `2.0` | CLAHE contrast enhancement |
| `--tile` | `8` | CLAHE tile grid size |
| `--mode` | `pingpong` | Playback: `forward` or `pingpong` |
| `--pause` | `5` | Pause frames at ends (pingpong) |
| `--cycles` | `1` | Pingpong repeats |
| `--psize` | `3` | Particle marker radius |
| `--no-parallel` | — | Disable parallel rendering |

## Examples

```bash
# Forward play at 30 fps
python mrc2movie.py -m tilt.mrc -o tilt.avi -f 30

# Pingpong with 3 cycles
python mrc2movie.py -m tomo.mrc -o tomo.avi --mode pingpong --cycles 3

# Downsampled, enhanced contrast
python mrc2movie.py -m large.mrc -o small.avi -b 2 --clip-limit 5

# Specific slice range with particles
python mrc2movie.py -m data.mrc -p coords.txt -o clip.avi --start 10 --end 50

# CLAHE for low-SNR tilt series
python mrc2movie.py -m ts.mrc -o ts.avi --clip-limit 100 --tile 16
```

## Dependencies

- Python ≥ 3.11
- [mrcfile](https://github.com/ccpem/mrcfile) — MRC file I/O
- [numpy](https://numpy.org/) — array operations
- [opencv-python](https://github.com/opencv/opencv-python) — CLAHE, video encoding
- [tqdm](https://github.com/tqdm/tqdm) — progress bars
