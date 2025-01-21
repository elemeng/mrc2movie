import argparse
from mrc_utils import read_tomogram, discard_slices, write_slices_to_png
import os
import logging

def main():
    parser = argparse.ArgumentParser(description="Convert MRC tomograms to PNG slices.")
    parser.add_argument("input_path", help="Path to the input MRC file.")
    parser.add_argument("output_dir", help="Directory to save output PNG files.")
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
        "--output_size",
        type=int,
        default=1024,
        help="Resize output images to a maximum dimension of SIZE",
    )
    parser.add_argument(
        "--clip_limit",
        type=float,
        default=2.0,
        help="CLAHE clip limit for contrast enhancement",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Read tomogram
    tomogram = read_tomogram(args.input_path)
    if tomogram is None:
        return

    # Discard slices if specified
    tomogram = discard_slices(tomogram, args.discard_range, args.discard_percentage)
    logging.info(f"Tomogram shape after discarding slices: {tomogram.shape}")

    # Save PNGs
    basename = os.path.splitext(os.path.basename(args.input_path))[0]
    write_slices_to_png(args.output_dir, basename, tomogram, args.output_size, args.clip_limit)

    logging.info("PNG conversion complete.")
    print("PNG conversion complete.")


if __name__ == "__main__":
    main()
