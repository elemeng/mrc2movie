from typing import Optional, Tuple, List
import argparse
import os
import mrcfile
import numpy as np
import cv2
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    filename="mrc2movie.log",  # Log file name
    level=logging.INFO,  # Log info and errors
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    filemode="w",  # Overwrite log file each run
)

# Constants
MAX_WORKERS = min(32, os.cpu_count() * 4)  # Optimal number of parallel workers
PNG_QUALITY = 9  # Maximum compression quality (0-9)
PNG_SUFFIX = "_slices"  # Suffix for PNG output directory


def normalize_slice(slice_data: np.ndarray, global_min: float, global_max: float) -> np.ndarray:
    """
    Normalize a single slice to 0-255 using global min and max.

    Args:
        slice_data: Input slice data as a numpy array.
        global_min: Global minimum value for normalization.
        global_max: Global maximum value for normalization.

    Returns:
        Normalized slice as an 8-bit unsigned integer array.
    """
    slice_float = slice_data.astype(np.float32)
    slice_float -= global_min
    if global_max > global_min:  # Avoid division by zero
        slice_float /= global_max - global_min
    slice_float *= 255
    return slice_float.astype(np.uint8)


def process_slice(args: Tuple[np.ndarray, float, float, float, int]) -> np.ndarray:
    """
    Process a single slice (normalize + CLAHE).

    Args:
        args: A tuple containing:
            - slice_data: Input slice data.
            - global_min: Global minimum value for normalization.
            - global_max: Global maximum value for normalization.
            - clip_limit: CLAHE clip limit.
            - tile_grid_size: CLAHE tile grid size.

    Returns:
        Processed slice as an 8-bit unsigned integer array.
    """
    slice_data, global_min, global_max, clip_limit, tile_grid_size = args
    normalized_slice = normalize_slice(slice_data, global_min, global_max)

    # Initialize CLAHE inside the worker process
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
    return clahe.apply(normalized_slice)


async def read_tomogram_async(input_path: str) -> Optional[np.ndarray]:
    """
    Asynchronously read a tomogram using memory-mapped I/O.

    Args:
        input_path: Path to the input MRC file.

    Returns:
        Tomogram data as a numpy array, or None if an error occurs.
    """
    try:
        with mrcfile.mmap(input_path, mode="r") as mrc:
            tomogram = mrc.data
            logging.info(f"Read: {input_path} | Shape: {tomogram.shape} | Type: {tomogram.dtype}")
            return tomogram
    except Exception as e:
        logging.error(f"Error reading {input_path}: {str(e)}", exc_info=True)
        print(f"Error reading {input_path}: {str(e)}")
        return None


async def write_video_async(
    output_path: str,
    frames: List[np.ndarray],
    fps: float,
    width: int,
    height: int,
    codec: str,
    playback_direction: str,
    output_size: Optional[int] = None,
) -> None:
    """
    Asynchronously write frames to a video file.

    Args:
        output_path: Output file path.
        frames: List of frames to write.
        fps: Frame rate.
        width: Original frame width.
        height: Original frame height.
        codec: Video codec.
        playback_direction: Playback direction ("forward" or "forward-backward").
        output_size: Optional maximum dimension for output. Defaults to None.
    """
    try:
        # Calculate output dimensions if size specified
        if output_size:
            scale = min(output_size / max(width, height), 1.0)  # Don't upscale
            new_width = int(width * scale)
            new_height = int(height * scale)
        else:
            new_width = width
            new_height = height

        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height), isColor=False)

        # Write forward frames
        for frame in frames:
            out.write(frame)

        # Write reverse frames if playback_direction is "forward-backward"
        if playback_direction == "forward-backward":
            for frame in reversed(frames[1:-1]):  # Exclude first and last to avoid duplicates
                out.write(frame)

        out.release()
        logging.info(f"Saved: {output_path}")
    except Exception as e:
        logging.error(f"Error writing {output_path}: {str(e)}", exc_info=True)
        print(f"Error writing {output_path}: {str(e)}")


def discard_slices(
    tomogram: np.ndarray,
    discard_range: Optional[Tuple[int, int]] = None,
    discard_percentage: Optional[Tuple[float, float]] = None,
) -> np.ndarray:
    """
    Discard slices based on range or percentage.

    Args:
        tomogram: Input tomogram data.
        discard_range: Optional tuple (start, end) for slice range to discard.
        discard_percentage: Optional tuple (start_percent, end_percent) for percentage-based discarding.

    Returns:
        Tomogram with slices discarded.

    Raises:
        ValueError: If discard_range or discard_percentage is invalid.
    """
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


def write_slices_to_png(
    output_dir: str,
    basename: str,
    slices: np.ndarray,
    output_size: Optional[int] = None,
) -> None:
    """
    Write processed slices to PNG files using parallel I/O operations.

    Args:
        output_dir: Path to main output directory where PNG subdirectory will be created.
        basename: Base name for output directory and files (without extension).
        slices: 3D numpy array of processed slices (height, width, num_slices).
        output_size: Optional maximum dimension for output images. If provided,
            images will be resized maintaining aspect ratio. None preserves original size.

    Raises:
        ValueError: If input parameters are invalid.
        IOError: If unable to create output directory or write files.
    """
    # Validate inputs
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("output_dir must be a non-empty string")
    if not isinstance(basename, str) or not basename:
        raise ValueError("basename must be a non-empty string")
    if not isinstance(slices, np.ndarray) or slices.ndim != 3:
        raise ValueError("slices must be a 3D numpy array")
    if output_size is not None and (not isinstance(output_size, int) or output_size <= 0):
        raise ValueError("output_size must be a positive integer or None")

    # Create PNG output subdirectory within main output directory
    png_dir = os.path.join(output_dir, f"{basename}_slices")
    os.makedirs(png_dir, exist_ok=True)

    # Get original dimensions
    height, width = slices[0].shape[:2]

    # Calculate scale factor if output_size specified
    if output_size:
        scale = min(output_size / max(width, height), 1.0)  # Don't upscale
        new_width = int(width * scale)
        new_height = int(height * scale)
    else:
        new_width = width
        new_height = height

    def write_single_png(slice: np.ndarray, index: int) -> Optional[str]:
        """Write a single slice to PNG with error handling."""
        try:
            # Convert to 8-bit if needed
            if slice.dtype != np.uint8:
                slice = cv2.normalize(slice, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

            # Resize if needed
            if output_size:
                slice = cv2.resize(slice, (new_width, new_height), interpolation=cv2.INTER_AREA)

            # Format filename with 4-digit number
            filename = os.path.join(png_dir, f"{basename}_{index:04d}.png")
            success = cv2.imwrite(filename, slice)
            if not success:
                raise IOError(f"Failed to write {filename}")
            return filename
        except Exception as e:
            logging.error(f"Error writing slice {index}: {str(e)}")
            return None

    # Use ThreadPoolExecutor for parallel I/O
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Create futures for all slices
        futures = {
            executor.submit(write_single_png, slice, i): i
            for i, slice in enumerate(slices)
        }

        # Track progress and handle results
        with tqdm(total=len(slices), desc="Writing PNGs") as pbar:
            for future in as_completed(futures):
                index = futures[future]
                try:
                    result = future.result()
                    if result:
                        pbar.update(1)
                except Exception as e:
                    logging.error(f"Error processing slice {index}: {str(e)}")
                    pbar.update(1)


async def process_tomogram_async(
    input_path: str,
    output_path: str,
    fps: float,
    clip_limit: float,
    tile_grid_size: int,
    codec: str,
    playback_direction: str,
    discard_range: Optional[Tuple[int, int]],
    discard_percentage: Optional[Tuple[float, float]],
    save_png: bool = False,
    output_size: int = 1024,
) -> None:
    """
    Process a single tomogram asynchronously.

    Args:
        input_path: Path to the input MRC file.
        output_path: Path to the output video file.
        fps: Frame rate for the output video.
        clip_limit: CLAHE clip limit for contrast enhancement.
        tile_grid_size: CLAHE tile grid size.
        codec: Video codec.
        playback_direction: Playback direction ("forward" or "forward-backward").
        discard_range: Optional tuple (start, end) for slice range to discard.
        discard_percentage: Optional tuple (start_percent, end_percent) for percentage-based discarding.
        save_png: Whether to save processed slices as PNG files.
        output_size: Maximum dimension for output images/video.
    """
    try:
        # Read tomogram (I/O-bound)
        tomogram = await read_tomogram_async(input_path)
        if tomogram is None:
            return

        # Check array dimensions
        if tomogram.ndim == 2:
            # Handle single frame as 3D array with one slice
            tomogram = np.expand_dims(tomogram, axis=0)
        elif tomogram.ndim != 3:
            raise ValueError(f"Skipping {input_path}: Not a 2D or 3D array.")

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
            write_slices_to_png(os.path.dirname(output_path), basename, np.array(tomogram_eq), output_size)

        # Write video (I/O-bound)
        height, width = tomogram.shape[1], tomogram.shape[2]
        await write_video_async(
            output_path, tomogram_eq, fps, width, height, codec, playback_direction, output_size
        )
    except Exception as e:
        # Log the error and continue
        logging.error(f"Error processing {input_path}: {str(e)}", exc_info=True)
        print(f"Error processing {input_path}: {str(e)}")


async def main() -> None:
    """Main function to process MRC tomograms into movies."""
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
        help="Save processed slices as PNG files in addition to video output. "
             "Files will be saved in a subdirectory named '{basename}_slices' "
             "with filenames formatted as '{basename}_0001.png', '{basename}_0002.png', etc. "
             "Images are saved with maximum quality and optional resizing based on --output_size.",
    )
    parser.add_argument(
        "--output_size",
        type=int,
        default=1024,
        help="Maximum dimension for output images/video (default: 1024).",
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
        output_path = os.path.join(args.output_dir, f"{os.path.splitext(mrc_file)[0]}.avi")
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
                args.output_size,
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