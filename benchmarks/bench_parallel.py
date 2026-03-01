#!/usr/bin/env python3
"""Benchmark parallel file processing in deep-diff.

Usage:
    uv run python benchmarks/bench_parallel.py [--files N] [--size BYTES] [--iters N]

Generates test data, then runs content and text comparisons with different
worker counts, reporting wall-clock time for each configuration.
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from deep_diff.core.comparator import Comparator
from deep_diff.core.models import DiffDepth


def generate_test_data(
    root: Path,
    *,
    num_files: int,
    file_size: int,
    modified_fraction: float = 0.5,
) -> tuple[Path, Path]:
    """Generate left/ and right/ directories with known differences.

    Args:
        root: Parent directory to create left/ and right/ under.
        num_files: Total number of files to create in each side.
        file_size: Approximate size of each file in bytes.
        modified_fraction: Fraction of files that differ between sides.

    Returns:
        Tuple of (left_dir, right_dir).
    """
    left = root / "left"
    right = root / "right"
    left.mkdir()
    right.mkdir()

    lines_per_file = max(1, file_size // 20)

    for i in range(num_files):
        name = f"file_{i:05d}.txt"
        content_left = "".join(
            f"line {i}-{j}: original content here\n" for j in range(lines_per_file)
        )

        if i < int(num_files * modified_fraction):
            content_right = "".join(
                f"line {i}-{j}: modified content here\n" for j in range(lines_per_file)
            )
        else:
            content_right = content_left

        (left / name).write_text(content_left)
        (right / name).write_text(content_right)

    return left, right


def run_benchmark(
    left: Path,
    right: Path,
    depth: DiffDepth,
    max_workers: int,
    iterations: int,
) -> float:
    """Run comparison and return average wall-clock seconds."""
    times: list[float] = []
    for _ in range(iterations):
        comp = Comparator(depth, max_workers=max_workers)
        start = time.perf_counter()
        comp.compare(left, right)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return sum(times) / len(times)


def main() -> None:
    """Run the benchmark suite."""
    parser = argparse.ArgumentParser(description="Benchmark parallel file processing")
    parser.add_argument("--files", type=int, default=200, help="Number of files per side")
    parser.add_argument("--size", type=int, default=4096, help="Approx file size in bytes")
    parser.add_argument("--iters", type=int, default=3, help="Iterations per configuration")
    args = parser.parse_args()

    console = Console()
    worker_configs = [1, 2, 4, 8, 0]

    with tempfile.TemporaryDirectory() as tmpdir:
        console.print(
            f"\nGenerating {args.files} files of ~{args.size} bytes each...\n",
            style="bold",
        )
        left, right = generate_test_data(
            Path(tmpdir),
            num_files=args.files,
            file_size=args.size,
        )

        for depth in [DiffDepth.content, DiffDepth.text]:
            table = Table(
                title=(
                    f"depth={depth.value}  |  files={args.files}"
                    f"  |  ~{args.size}B each  |  {args.iters} iters"
                ),
            )
            table.add_column("Workers", style="cyan", justify="right")
            table.add_column("Avg Time (s)", style="green", justify="right")
            table.add_column("Speedup", style="yellow", justify="right")

            serial_time: float | None = None
            for workers in worker_configs:
                label = "auto" if workers == 0 else str(workers)
                avg = run_benchmark(left, right, depth, workers, args.iters)
                if workers == 1:
                    serial_time = avg
                speedup = f"{serial_time / avg:.2f}x" if serial_time else "baseline"
                table.add_row(label, f"{avg:.4f}", speedup)

            console.print(table)
            console.print()


if __name__ == "__main__":
    main()
