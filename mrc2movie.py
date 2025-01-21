import argparse
import os
import mrcfile
import numpy as np
import cv2
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import logging
import asyncio

# Configure logging
logging.basicConfig(
    filename="mrc2movie.log",  # Log file name
    level=logging.INFO,  # Log info and errors
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    filemode="w",  # Overwrite log file each run
)


def normalize_slice(slice_data, global_min, global_max):
    """Normalize a single slice to 0-255 using global min and max."""
    slice_float = slice_data.astype(np.float32)
    slice_float -= global_min
    if global_max > global_min:  # Avoid division by zero
        slice_float /= global_max - global_min
    slice_float *= 255
    return slice_float.astype(np.uint8)


def process_slice(args):
    """Process a single slice (normalize + CLAHE)."""
    slice_data, global_min, global_max, clip_limit, tile_grid_size = args
    normalized_slice = normalize_slice(slice_data, global_min, global_max)

    # Initialize CLAHE inside the worker process
    clahe = cv2.createCLAHE(
        clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size)
    )
    return clahe.apply(normalized_slice)


async def read_tomogram_async(input_path):
    """Asynchronously read a tomogram using memory-mapped I/O."""
    try:
        with mrcfile.mmap(input_path, mode="r") as mrc:
            tomogram = mrc.data
            logging.info(
                f"Read: {input_path} | Shape: {tomogram.shape} | Type: {tomogram.dtype}"
            )
            return tomogram
    except Exception as e:
        logging.error(f"Error reading {input_path}: {str(e)}", exc_info=True)
        print(f"Error reading {input_path}: {str(e)}")
        return None


async def write_video_async(
    output_path, frames, fps, width, height, codec, playback_direction
):
    """Asynchronously write frames to a video file."""
    try:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height), isColor=False)

        # Write forward frames
        for frame in frames:
            out.write(frame)

        # Write reverse frames if playback_direction is "forward-backward"
        if playback_direction == "forward-backward":
            for frame in reversed(
                frames[1:-1]
            ):  # Exclude first and last to avoid duplicates
                out.write(frame)

        out.release()
        logging.info(f"Saved: {output_path}")
    except Exception as e:
        logging.error(f"Error writing {output_path}: {str(e)}", exc_info=True)
        print(f"Error writing {output_path}: {str(e)}")


def discard_slices(tomogram, discard_range=None, discard_percentage=None):
    """Discard slices based on range or percentage."""
    num_slices = tomogram.shape[0]

    if discard_range:
        start, end = discard_range
        if start < 0 or end > num_slices or start >= end:
            raise ValueError(f"Invalid discard range: {discard_range}")
        return tomogram[start:end]

    if discard_percentage:
        start_percent, end_percent = discard_percentage
        if not (0 <= start_percent < 1 and 0 <= end_percent < 1):
            raise ValueError(f"Invalid discard percentage: {discard_percentage}")
        start = int(num_slices * start_percent)
        end = int(num_slices * (1 - end_percent))
        return tomogram[start:end]

    return tomogram


def write_slices_to_png(basename, slices):
    """Write processed slices to PNG files.

    Args:
        basename (str): Base name for output directory and files
        slices (np.ndarray): Array of processed slices (height, width, num_slices)
    """
    # Create output directory
    output_dir = f"{basename}_slices"
    os.makedirs(output_dir, exist_ok=True)

    # Write each slice as PNG
    for i, slice in enumerate(slices):
        # Convert to 8-bit if needed
        if slice.dtype != np.uint8:
            slice = cv2.normalize(slice, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        # Format filename with 4-digit number
        filename = os.path.join(output_dir, f"{basename}_{i:04d}.png")
        cv2.imwrite(filename, slice)


async def process_tomogram_async(
    input_path,
    output_path,
    fps,
    clip_limit,
    tile_grid_size,
    codec,
    playback_direction,
    discard_range,
    discard_percentage,
    save_png=False,
):
    """Process a single tomogram asynchronously."""
    try:
        # Read tomogram (I/O-bound)
        tomogram = await read_tomogram_async(input_path)
        if tomogram is None:
            return

        # Check if the data is a 3D array
        if tomogram.ndim != 3:
            raise ValueError(f"Skipping {input_path}: Not a 3D array.")

        # Discard slices if specified
        tomogram = discard_slices(tomogram, discard_range, discard_percentage)
        logging.info(f"Tomogram shape after discarding slices: {tomogram.shape}")

        # Compute global min and max for consistent normalization
        global_min = tomogram.min()
        global_max = tomogram.max()
        logging.info(f"Global min: {global_min}, Global max: {global_max}")

        # Process slices in parallel (CPU-bound)
        num_processes = cpu_count()
        with Pool(processes=num_processes) as pool:
            slice_args = [
                (slice_data, global_min, global_max, clip_limit, tile_grid_size)
                for slice_data in tomogram
            ]
            tomogram_eq = list(
                tqdm(
                    pool.imap(process_slice, slice_args),
                    total=len(tomogram),
                    desc="Processing slices",
                )
            )

        # Save PNGs if enabled
        if save_png:
            basename = os.path.splitext(os.path.basename(input_path))[0]
            write_slices_to_png(basename, np.array(tomogram_eq))

        # Write video (I/O-bound)
        height, width = tomogram.shape[1], tomogram.shape[2]
        await write_video_async(
            output_path, tomogram_eq, fps, width, height, codec, playback_direction
        )
    except Exception as e:
        # Log the error and continue
        logging.error(f"Error processing {input_path}: {str(e)}", exc_info=True)
        print(f"Error processing {input_path}: {str(e)}")


async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Batch process MRC tomograms into movies with enhanced contrast."
    )
    parser.add_argument("input_dir", help="Directory containing MRC files.")
    parser.add_argument("output_dir", help="Directory to save output movies.")
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Frame rate for the output movie (default: 30.0).",
    )
    parser.add_argument(
        "--clip_limit",
        type=float,
        default=2.0,
        help="CLAHE clip limit for contrast enhancement (default: 2.0).",
    )
    parser.add_argument(
        "--tile_grid_size",
        type=int,
        default=8,
        help="CLAHE tile grid size (default: 8).",
    )
    parser.add_argument("--codec", default="MJPG", help="Video codec (default: MJPG).")
    parser.add_argument(
        "--playback",
        choices=["forward", "forward-backward"],
        default="forward-backward",
        help="Playback direction (default: forward-backward).",
    )
    parser.add_argument(
        "--discard_range",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Discard slices from START to END (0-based indexing).",
    )
    parser.add_argument(
        "--discard_percentage",
        nargs=2,
        type=float,
        metavar=("START_PERCENT", "END_PERCENT"),
        help="Discard START_PERCENT from the beginning and END_PERCENT from the end (e.g., 0.1 0.1).",
    )
    parser.add_argument(
        "--png",
        action="store_true",
        help="Save processed slices as PNG files in addition to video output.",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Find all MRC files in the input directory
    mrc_files = [f for f in os.listdir(args.input_dir) if f.endswith(".mrc")]
    if not mrc_files:
        logging.error(f"No MRC files found in {args.input_dir}.")
        print(f"No MRC files found in {args.input_dir}.")
        return

    # Process each MRC file asynchronously with a progress bar
    tasks = []
    for mrc_file in mrc_files:
        input_path = os.path.join(args.input_dir, mrc_file)
        output_path = os.path.join(
            args.output_dir, f"{os.path.splitext(mrc_file)[0]}.avi"
        )
        tasks.append(
            process_tomogram_async(
                input_path,
                output_path,
                args.fps,
                args.clip_limit,
                args.tile_grid_size,
                args.codec,
                args.playback,
                args.discard_range,
                args.discard_percentage,
                args.png,
            )
        )

    # Run all tasks concurrently with a progress bar
    with tqdm(total=len(tasks), desc="Processing tomograms") as pbar:
        for task in asyncio.as_completed(tasks):
            await task
            pbar.update(1)

    logging.info("Batch processing complete.")
    print("Batch processing complete.")


if __name__ == "__main__":
    asyncio.run(main())
