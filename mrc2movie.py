import argparse
import asyncio
from mrc_utils import (
    read_tomogram,
    discard_slices,
    write_slices_to_png,
    process_slice,
)
import numpy as np
from typing import Optional, Tuple, List
import cv2
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import logging
import os


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

        # Resize all frames to match output dimensions
        resized_frames = [
            cv2.resize(frame, (new_width, new_height)) for frame in frames
        ]

        fourcc = cv2.VideoWriter_fourcc(*codec)
        # Optimize video writer for better performance
        out = cv2.VideoWriter(
            output_path, fourcc, fps, (new_width, new_height), isColor=False
        )
        if not out.isOpened():
            raise IOError(f"Failed to open video writer for {output_path}")

        # Write forward frames
        for frame in resized_frames:
            out.write(frame)

        # Write reverse frames if playback_direction is "forward-backward"
        if playback_direction == "forward-backward":
            for frame in reversed(
                resized_frames[1:-1]
            ):  # Exclude first and last to avoid duplicates
                out.write(frame)

        out.release()

        logging.info(f"Saved: {output_path}")
    except Exception as e:
        logging.error(f"Error writing {output_path}: {str(e)}", exc_info=True)
        print(f"Error writing {output_path}: {str(e)}")


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
    """
    try:
        # Read tomogram (I/O-bound)
        tomogram = read_tomogram(input_path)
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
        # logging.info(f"Global min: {global_min}, Global max: {global_max}")

        # Process slices in parallel (CPU-bound) with optimized chunking
        num_processes = min(cpu_count(), len(tomogram))
        chunk_size = max(
            1, len(tomogram) // (num_processes * 4)
        )  # Smaller chunks for better load balancing

        with Pool(processes=num_processes) as pool:
            slice_args = [
                (slice_data, global_min, global_max, clip_limit, tile_grid_size)
                for slice_data in tomogram
            ]
            tomogram_eq = list(
                tqdm(
                    pool.imap(process_slice, slice_args, chunksize=chunk_size),
                    total=len(tomogram),
                    desc="Processing slices",
                )
            )
            # for frame in tomogram_eq:
            # logging.info(f"Frame min: {frame.min()}, Frame max: {frame.max()}")

        # Save PNGs if enabled
        if save_png:
            basename = os.path.splitext(os.path.basename(input_path))[0]
            write_slices_to_png(
                os.path.dirname(output_path),
                basename,
                np.array(tomogram_eq),
                output_size,
            )

        # Write video (I/O-bound)
        height, width = tomogram.shape[1], tomogram.shape[2]
        await write_video_async(
            output_path,
            tomogram_eq,
            fps,
            width,
            height,
            codec,
            playback_direction,
            output_size,
        )
    except Exception as e:
        # Log the error and continue
        logging.error(f"Error processing {input_path}: {str(e)}", exc_info=True)
        print(f"Error processing {input_path}: {str(e)}")


async def main():
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
        help="Frame rate for the output movie (default: 30.0, good for built tomogram; for tilt series, using 1~5 is better. Try other numbers by your self.).",
    )
    parser.add_argument(
        "--clip_limit",
        type=float,
        default=2.0,
        help="CLAHE clip limit for contrast enhancement (default: 2.0; try 30~1000 for tilt series, because their SNR is too low).",
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
    parser.add_argument(
        "--output_size",
        type=int,
        default=1024,
        help="Maximum dimension for output images/video (default: 1024).",
    )

    # Experimental parameter presets
    parser.add_argument(
        "--preset",
        choices=["tomogram", "tomo", "tiltseries", "ts", "quick", "max_quality"],
        help="Use optimized parameter presets for common data types.",
    )
    parser.add_argument(
        "--estimate_memory",
        action="store_true",
        help="Estimate memory usage before processing files.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable profiling mode with timing information.",
    )
    parser.add_argument(
        "--speed",
        choices=["fast", "balanced", "quality"],
        default="balanced",
        help="Speed vs quality trade-off preset.",
    )
    args = parser.parse_args()

    # Apply experimental presets
    if args.preset:
        preset_params = {
            "tomogram": {"fps": 30.0, "clip_limit": 2.0, "output_size": 1024},
            "tomo": {"fps": 30.0, "clip_limit": 2.0, "output_size": 1024},
            "tiltseries": {"fps": 8.0, "clip_limit": 100.0, "output_size": 1024},
            "ts": {"fps": 8.0, "clip_limit": 100.0, "output_size": 1024},
            "quick": {"fps": 15.0, "clip_limit": 2.0, "output_size": 512},
            "max_quality": {"fps": 30.0, "clip_limit": 5.0, "output_size": 2048},
        }
        preset = preset_params[args.preset]
        args.fps = preset["fps"]
        args.clip_limit = preset["clip_limit"]
        args.output_size = preset["output_size"]
        print(f"Applied {args.preset} preset: {preset}")


    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Find all MRC files in the input directory
    mrc_files = [f for f in os.listdir(args.input_dir) if f.endswith((".mrc", ".st"))]
    if not mrc_files:
        logging.error(f"No MRC files found in {args.input_dir}.")
        print(f"No MRC files found in {args.input_dir}.")
        return

    # Memory estimation mode
    if args.estimate_memory:
        from mrc_utils import estimate_memory_usage

        for mrc_file in mrc_files:
            input_path = os.path.join(args.input_dir, mrc_file)
            estimate_memory_usage(input_path)
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
