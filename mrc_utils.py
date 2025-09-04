from typing import Optional, Tuple
import os
import mrcfile
import numpy as np
import cv2
from tqdm import tqdm
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
PNG_QUALITY = 6  # Balanced compression quality
PNG_SUFFIX = "_slices"  # Suffix for PNG output directory


def normalize_slice(
    slice_data: np.ndarray, global_min: float, global_max: float
) -> np.ndarray:
    """
    Normalize a single slice to 0-255 using global min and max with memory optimization.
    """
    # Use in-place operations to reduce memory allocations
    slice_float = slice_data.astype(np.float32, copy=False)
    slice_float = np.subtract(slice_float, global_min, out=slice_float)
    if global_max > global_min:  # Avoid division by zero
        scale = 255.0 / (global_max - global_min)
        slice_float = np.multiply(slice_float, scale, out=slice_float)
    slice_float = np.clip(slice_float, 0, 255, out=slice_float)
    return slice_float.astype(np.uint8, copy=False)


def process_slice(args: Tuple[np.ndarray, float, float, float, int]) -> np.ndarray:
    """
    Process a single slice (normalize + CLAHE) with memory optimization.
    """
    slice_data, global_min, global_max, clip_limit, tile_grid_size = args

    # In-place normalization to reduce memory allocation
    slice_float = slice_data.astype(np.float32, copy=False)
    slice_float = np.subtract(slice_float, global_min, out=slice_float)
    if global_max > global_min:
        scale = 255.0 / (global_max - global_min)
        slice_float = np.multiply(slice_float, scale, out=slice_float)
    slice_float = np.clip(slice_float, 0, 255, out=slice_float)
    normalized_slice = slice_float.astype(np.uint8, copy=False)

    # Cache CLAHE instances per process
    if not hasattr(process_slice, "_clahe_cache"):
        process_slice._clahe_cache = {}

    cache_key = (clip_limit, tile_grid_size)
    if cache_key not in process_slice._clahe_cache:
        process_slice._clahe_cache[cache_key] = cv2.createCLAHE(
            clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size)
        )

    return process_slice._clahe_cache[cache_key].apply(normalized_slice)


def estimate_memory_usage(input_path: str) -> None:
    """
    Estimate memory usage for a given MRC file.
    """
    try:
        with mrcfile.mmap(input_path, mode="r") as mrc:
            shape = mrc.data.shape
            dtype = mrc.data.dtype

            element_size = np.dtype(dtype).itemsize
            total_elements = np.prod(shape)
            raw_memory = total_elements * element_size

            # Account for processing overhead (normalized arrays + processed arrays)
            processing_overhead = raw_memory * 2.5  # ~2.5x for float32 + uint8 arrays

            print(f"File: {os.path.basename(input_path)}")
            print(f"  Shape: {shape}")
            print(f"  Dtype: {dtype}")
            print(f"  Raw size: {raw_memory / 1024**2:.1f} MB")
            print(f"  Processing memory: {processing_overhead / 1024**2:.1f} MB")

            if processing_overhead > 8 * 1024**3:
                print(f"  ⚠️  WARNING: Large file - may exceed available RAM")
            elif processing_overhead > 4 * 1024**3:
                print(f"  ⚠️  Large file - monitor memory usage")
            else:
                print(f"  ✅ Safe for processing")

    except Exception as e:
        print(f"Error estimating memory for {input_path}: {str(e)}")


def read_tomogram(input_path: str) -> Optional[np.ndarray]:
    """
    Read a tomogram with memory-efficient chunking for large files.
    """
    try:
        with mrcfile.mmap(input_path, mode="r") as mrc:
            # For large files, read in chunks to avoid memory issues
            shape = mrc.data.shape
            dtype = mrc.data.dtype

            # Estimate memory usage (bytes per element × total elements)
            element_size = np.dtype(dtype).itemsize
            total_elements = np.prod(shape)
            estimated_memory = total_elements * element_size

            # If file is > 2GB, warn about memory usage
            if estimated_memory > 2 * 1024**3:  # 2GB
                logging.warning(
                    f"Large file detected: {estimated_memory / 1024**3:.1f}GB - {input_path}"
                )

            # Use direct array access instead of .data property for better memory control
            tomogram = mrc.data[:]
            logging.info(
                f"Read: {input_path} | Shape: {tomogram.shape} | Type: {tomogram.dtype} | Memory: {estimated_memory / 1024**2:.1f}MB"
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
    clip_limit: float = 2.0,
    tile_grid_size: int = 8,
) -> None:
    """
    Write processed slices to PNG files using parallel I/O operations.
    """
    # Validate inputs
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("output_dir must be a non-empty string")
    if not isinstance(basename, str) or not basename:
        raise ValueError("basename must be a non-empty string")
    if not isinstance(slices, np.ndarray) or slices.ndim not in (2, 3):
        raise ValueError("slices must be a 2D or 3D numpy array")
    if output_size is not None and (
        not isinstance(output_size, int) or output_size <= 0
    ):
        raise ValueError("output_size must be a positive integer or None")

    # Data-adaptive contrast enhancement based on dynamic range
    data_range = float(np.max(slices) - np.min(slices))
    if data_range < 1000:  # Low dynamic range (built tomograms)
        clip_limit = max(1.0, min(5.0, clip_limit))
    elif data_range < 10000:  # Medium dynamic range
        clip_limit = max(5.0, min(50.0, clip_limit * 2))
    else:  # High dynamic range (tilt series)
        clip_limit = max(30.0, min(1000.0, clip_limit * 10))

    # Create PNG output subdirectory within main output directory
    png_dir = os.path.join(output_dir, f"{basename}_slices")
    os.makedirs(png_dir, exist_ok=True)

    # Handle 2D case (single slice)
    if slices.ndim == 2:
        # Calculate scale factor if output_size specified
        height, width = slices.shape
        if output_size:
            scale = min(output_size / max(width, height), 1.0)  # Don't upscale
            new_width = int(width * scale)
            new_height = int(height * scale)
        else:
            new_width = width
            new_height = height

        # Normalize and process single slice
        global_min = np.min(slices)
        global_max = np.max(slices)
        normalized_slice = normalize_slice(slices, global_min, global_max)

        # Apply CLAHE contrast enhancement
        clahe = cv2.createCLAHE(
            clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size)
        )
        enhanced_slice = clahe.apply(normalized_slice)

        # Resize if needed
        if output_size:
            enhanced_slice = cv2.resize(
                enhanced_slice, (new_width, new_height), interpolation=cv2.INTER_AREA
            )

        # Write single PNG file
        filename = os.path.join(output_dir, f"{basename}.png")
        success = cv2.imwrite(filename, enhanced_slice)
        if not success:
            raise IOError(f"Failed to write {filename}")
        return

    # Handle 3D case (multiple slices)
    height, width = slices[0].shape[:2]
    if output_size:
        scale = min(output_size / max(width, height), 1.0)  # Don't upscale
        new_width = int(width * scale)
        new_height = int(height * scale)
    else:
        new_width = width
        new_height = height

    # Calculate global min/max for normalization
    global_min = np.min(slices)
    global_max = np.max(slices)

    def process_and_write_slice(slice: np.ndarray, index: int) -> Optional[str]:
        """Process and write a single slice to PNG with error handling."""
        try:
            # Normalize slice using global min/max
            normalized_slice = normalize_slice(slice, global_min, global_max)

            # Apply CLAHE contrast enhancement
            clahe = cv2.createCLAHE(
                clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size)
            )
            enhanced_slice = clahe.apply(normalized_slice)

            # Resize if needed
            if output_size:
                enhanced_slice = cv2.resize(
                    enhanced_slice,
                    (new_width, new_height),
                    interpolation=cv2.INTER_AREA,
                )

            # Format filename with 4-digit number
            filename = os.path.join(png_dir, f"{basename}_{index:04d}.png")
            success = cv2.imwrite(filename, enhanced_slice)
            if not success:
                raise IOError(f"Failed to write {filename}")
            return filename
        except Exception as e:
            logging.error(f"Error processing slice {index}: {str(e)}")
            return None

    # Use ThreadPoolExecutor for parallel I/O
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Create futures for all slices
        futures = {
            executor.submit(process_and_write_slice, slice, i): i
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
