from typing import Optional, Tuple
import os
import mrcfile
import numpy as np
import cv2
import tqdm
import logging
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


def normalize_slice(
    slice_data: np.ndarray, global_min: float, global_max: float
) -> np.ndarray:
    """
    Normalize a single slice to 0-255 using global min and max.
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
    """
    slice_data, global_min, global_max, clip_limit, tile_grid_size = args
    normalized_slice = normalize_slice(slice_data, global_min, global_max)

    # Initialize CLAHE inside the worker process
    clahe = cv2.createCLAHE(
        clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size)
    )
    return clahe.apply(normalized_slice)


def read_tomogram(input_path: str) -> Optional[np.ndarray]:
    """
    Read a tomogram using memory-mapped I/O.
    """
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


def discard_slices(
    tomogram: np.ndarray,
    discard_range: Optional[Tuple[int, int]] = None,
    discard_percentage: Optional[Tuple[float, float]] = None,
) -> np.ndarray:
    """
    Discard slices based on range or percentage.
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
    """
    # Validate inputs
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("output_dir must be a non-empty string")
    if not isinstance(basename, str) or not basename:
        raise ValueError("basename must be a non-empty string")
    if not isinstance(slices, np.ndarray) or slices.ndim != 3:
        raise ValueError("slices must be a 3D numpy array")
    if output_size is not None and (
        not isinstance(output_size, int) or output_size <= 0
    ):
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
                slice = cv2.normalize(
                    slice, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U
                )

            # Resize if needed
            if output_size:
                slice = cv2.resize(
                    slice, (new_width, new_height), interpolation=cv2.INTER_AREA
                )

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
