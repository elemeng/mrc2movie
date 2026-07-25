#!/usr/bin/env python3
"""
Convert MRC tomograms to video with optional particle overlay.

Particles can come from:
  -i model.mod     IMOD binary file (auto-detected, pure Python parser)
  -p particles.txt text file, one "x y z" per line

Dependencies: pip install mrcfile numpy opencv-python tqdm
"""

import argparse
import struct
import sys
from multiprocessing import Pool, cpu_count

import cv2
import numpy as np
from tqdm import tqdm

try:
    import mrcfile
except ImportError:
    print("Missing: pip install mrcfile numpy opencv-python tqdm")
    sys.exit(1)


# ═════════════════════════════════════════════════════════════════════════════
#  IMOD parser — try native bindings first, then pure Python fallback
# ═════════════════════════════════════════════════════════════════════════════

try:
    import imodfile as _imodfile
    _HAS_IMOD_NATIVE = True
except ImportError:
    _HAS_IMOD_NATIVE = False

_ID_OBJT = 0x4F424A54  # b"OBJT"
_ID_CONT = 0x434F4E54  # b"CONT"
_ID_POIN = 0x504F494E  # b"POIN"
_ID_IEOF = 0x49454F46  # b"IEOF"


def _iter_chunks(data: bytes, start: int = 0):
    """Yield (chunk_id, chunk_data) from big-endian IMOD binary."""
    off = start
    while off + 8 <= len(data):
        cid = struct.unpack_from(">I", data, off)[0]
        if cid == _ID_IEOF:
            break
        size = struct.unpack_from(">I", data, off + 4)[0]
        if size == 0:
            off += 8
            continue
        chunk = data[off + 8: off + 8 + size]
        off += 8 + size
        if off % 4:
            off += 4 - (off % 4)
        yield cid, chunk


def load_imod_points(path: str) -> list[tuple[float, float, float]]:
    """Read all contour points from an IMOD binary file.

    Uses the native Rust imodfile bindings when available,
    falls back to a pure Python parser otherwise.
    """
    if _HAS_IMOD_NATIVE:
        model = _imodfile.load(path)
        arr = model.points()  # (N, 3) float32 numpy array
        return [(float(arr[i, 0]), float(arr[i, 1]), float(arr[i, 2]))
                for i in range(arr.shape[0])]

    # Pure Python fallback
    with open(path, "rb") as f:
        data = f.read()
    pts = []
    for cid, chunk in _iter_chunks(data):
        if cid == _ID_OBJT:
            _walk_obj(chunk, pts)
    return pts


def _walk_obj(data: bytes, pts: list):
    for cid, chunk in _iter_chunks(data):
        if cid == _ID_CONT:
            _walk_cont(chunk, pts)


def _walk_cont(data: bytes, pts: list):
    for cid, chunk in _iter_chunks(data):
        if cid == _ID_POIN:
            for i in range(len(chunk) // 12):
                off = i * 12
                x, y, z = struct.unpack_from(">fff", chunk, off)
                pts.append((x, y, z))


# ═════════════════════════════════════════════════════════════════════════════
#  Particle loading
# ═════════════════════════════════════════════════════════════════════════════

def load_txt_particles(path: str) -> list[tuple[float, float, float]]:
    """Read x y z particles from a text file."""
    pts = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", " ").split()
            if len(parts) < 3:
                continue
            try:
                pts.append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError:
                continue
    return pts


# ═════════════════════════════════════════════════════════════════════════════
#  Slice rendering
# ═════════════════════════════════════════════════════════════════════════════

def render_slice(args: tuple) -> np.ndarray:
    """Normalize → CLAHE → RGB → draw particles → BGR frame."""
    (slice_data, vmin, vmax, clip_limit, tile_size,
     particles, psize, z, bin_f) = args

    if vmax > vmin:
        img = np.clip((slice_data.astype(np.float32) - vmin) *
                      (255.0 / (vmax - vmin)), 0, 255).astype(np.uint8)
    else:
        img = np.zeros_like(slice_data, dtype=np.uint8)

    clahe = cv2.createCLAHE(clipLimit=clip_limit,
                            tileGridSize=(tile_size, tile_size))
    img = clahe.apply(img)
    frame = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    if particles and psize > 0:
        h, w = frame.shape[:2]
        for px, py, pz in particles:
            dz = abs(pz - z)
            if dz <= psize:
                cx, cy = int(px / bin_f), int(py / bin_f)
                if 0 <= cx < w and 0 <= cy < h:
                    r = max(1, round(psize * (1.0 - dz / max(psize, 1))))
                    cv2.circle(frame, (cx, cy), r, (0, 0, 255), -1)

    return frame


def slice_sequence(start: int, end: int, mode: str,
                   pause: int, cycles: int) -> list[int]:
    if mode == "forward":
        return list(range(start, end + 1))
    seq = []
    for c in range(cycles):
        seq += list(range(start, end + 1))
        if c < cycles - 1:
            seq += [end] * pause
        seq += list(range(end - 1, start - 1, -1))
        if c < cycles - 1:
            seq += [start] * pause
    return seq


# ═════════════════════════════════════════════════════════════════════════════
#  CLI
# ═════════════════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="MRC tomogram → video")
    p.add_argument("-m", "--mrc", required=True, help="MRC input file")
    p.add_argument("-i", "--imod", help="IMOD particle file (.mod)")
    p.add_argument("-p", "--particles", help="Particle text file (x y z per line)")
    p.add_argument("-o", "--output", default="output.avi")
    p.add_argument("-f", "--fps", type=float, default=10)
    p.add_argument("-b", "--bin", type=int, default=1, dest="bin_factor",
                   help="Downsample factor")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=0, help="0 = last slice")
    p.add_argument("--clip-limit", type=float, default=2.0, help="CLAHE contrast")
    p.add_argument("--tile", type=int, default=8, help="CLAHE tile size")
    p.add_argument("--mode", choices=["forward", "pingpong"], default="pingpong")
    p.add_argument("--pause", type=int, default=5)
    p.add_argument("--cycles", type=int, default=1)
    p.add_argument("--psize", type=int, default=3, help="Particle radius")
    p.add_argument("--no-parallel", action="store_false", dest="parallel",
                   default=True)
    args = p.parse_args()

    # Read MRC
    print(f"📁 {args.mrc}")
    with mrcfile.mmap(args.mrc, mode="r") as mrc:
        vol = mrc.data
    nz, ny, nx = vol.shape
    print(f"📊 {nx}×{ny}×{nz}")

    # Read particles
    particles = []
    if args.imod:
        print(f"📁 IMOD: {args.imod}")
        particles = load_imod_points(args.imod)
        print(f"📌 {len(particles)} particles")
    if args.particles:
        print(f"📁 Particles: {args.particles}")
        particles = load_txt_particles(args.particles)
        print(f"📌 {len(particles)} particles")

    # Slice range
    start = args.start
    end = args.end if args.end != 0 else nz - 1
    end = min(end, nz - 1)
    if start > end:
        print(f"❌ start {start} > end {end}")
        sys.exit(1)

    seq = slice_sequence(start, end, args.mode, args.pause, args.cycles)
    total = len(seq)
    print(f"🎬 {total} frames, {total/args.fps:.1f}s @ {args.fps}fps")

    out_w, out_h = nx // args.bin_factor, ny // args.bin_factor
    print(f"📐 {out_w}×{out_h}")

    vol = np.array(vol, dtype=np.float32, copy=False)
    vmin, vmax = float(vol.min()), float(vol.max())

    # Render
    print("🎨 Rendering...")
    jobs = [(vol[z], vmin, vmax, args.clip_limit, args.tile,
             particles, args.psize, z, args.bin_factor) for z in seq]
    if args.parallel and len(jobs) > 1:
        with Pool(min(cpu_count(), len(jobs))) as pool:
            frames = list(tqdm(pool.imap(render_slice, jobs), total=len(jobs)))
    else:
        frames = [render_slice(j) for j in tqdm(jobs)]

    # Encode
    print(f"🎞️ {args.output}")
    w = cv2.VideoWriter(args.output, cv2.VideoWriter_fourcc(*"MJPG"),
                        args.fps, (out_w, out_h))
    if not w.isOpened():
        w = cv2.VideoWriter(args.output, cv2.VideoWriter_fourcc(*"I420"),
                            args.fps, (out_w, out_h))
    for f in tqdm(frames):
        w.write(f)
    w.release()
    print(f"✅ {args.output}")


if __name__ == "__main__":
    main()
