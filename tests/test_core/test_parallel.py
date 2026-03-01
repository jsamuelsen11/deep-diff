"""Tests for parallel file processing in deep_diff.core.comparator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from deep_diff.core.comparator import Comparator
from deep_diff.core.models import DiffDepth, FileStatus

if TYPE_CHECKING:
    from pathlib import Path


class TestResolveWorkers:
    """Verify _resolve_workers() auto-detection and pass-through."""

    def test_workers_0_auto_detects(self) -> None:
        c = Comparator(max_workers=0)
        with patch("deep_diff.core.comparator.os.cpu_count", return_value=4):
            assert c._resolve_workers() == 8  # min(32, 4 + 4)

    def test_workers_0_with_none_cpu_count(self) -> None:
        c = Comparator(max_workers=0)
        with patch("deep_diff.core.comparator.os.cpu_count", return_value=None):
            assert c._resolve_workers() == 5  # min(32, 1 + 4)

    def test_workers_0_capped_at_32(self) -> None:
        c = Comparator(max_workers=0)
        with patch("deep_diff.core.comparator.os.cpu_count", return_value=64):
            assert c._resolve_workers() == 32

    def test_workers_1_returns_1(self) -> None:
        c = Comparator(max_workers=1)
        assert c._resolve_workers() == 1

    def test_workers_explicit_passes_through(self) -> None:
        c = Comparator(max_workers=8)
        assert c._resolve_workers() == 8


def _make_mixed_dirs(tmp_path: Path, *, num_paired: int = 5) -> tuple[Path, Path]:
    """Create left/right dirs with identical, modified, added, and removed files."""
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()

    # Paired identical files
    for i in range(num_paired):
        (left / f"same_{i:03d}.txt").write_text(f"content {i}\n")
        (right / f"same_{i:03d}.txt").write_text(f"content {i}\n")

    # Paired modified files
    for i in range(num_paired):
        (left / f"mod_{i:03d}.txt").write_text(f"original {i}\n")
        (right / f"mod_{i:03d}.txt").write_text(f"changed {i}\n")

    # Added (right only)
    (right / "added.txt").write_text("new file\n")

    # Removed (left only)
    (left / "removed.txt").write_text("old file\n")

    return left, right


class TestParallelContentPipeline:
    """Verify parallel content pipeline produces correct results."""

    def test_parallel_matches_serial(self, tmp_path: Path) -> None:
        left, right = _make_mixed_dirs(tmp_path)
        serial = Comparator(DiffDepth.content, max_workers=1).compare(left, right)
        parallel = Comparator(DiffDepth.content, max_workers=4).compare(left, right)
        assert serial.comparisons == parallel.comparisons
        assert serial.stats == parallel.stats

    def test_parallel_preserves_order(self, tmp_path: Path) -> None:
        left, right = _make_mixed_dirs(tmp_path, num_paired=20)
        result = Comparator(DiffDepth.content, max_workers=4).compare(left, right)
        paths = [c.relative_path for c in result.comparisons]
        assert paths == sorted(paths)

    def test_all_added_passthrough(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        for i in range(5):
            (right / f"file_{i}.txt").write_text(f"added {i}\n")

        result = Comparator(DiffDepth.content, max_workers=4).compare(left, right)
        assert all(c.status == FileStatus.added for c in result.comparisons)
        assert result.stats.added == 5

    def test_all_removed_passthrough(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        for i in range(5):
            (left / f"file_{i}.txt").write_text(f"removed {i}\n")

        result = Comparator(DiffDepth.content, max_workers=4).compare(left, right)
        assert all(c.status == FileStatus.removed for c in result.comparisons)
        assert result.stats.removed == 5

    def test_empty_dirs(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        result = Comparator(DiffDepth.content, max_workers=4).compare(left, right)
        assert result.comparisons == ()

    def test_single_pair_skips_executor(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "only.txt").write_text("a\n")
        (right / "only.txt").write_text("b\n")

        with patch("deep_diff.core.comparator.ThreadPoolExecutor") as mock_executor:
            result = Comparator(DiffDepth.content, max_workers=4).compare(left, right)
            mock_executor.assert_not_called()
        assert len(result.comparisons) == 1

    def test_hashes_populated_for_paired_files(self, tmp_path: Path) -> None:
        left, right = _make_mixed_dirs(tmp_path)
        result = Comparator(DiffDepth.content, max_workers=4).compare(left, right)
        for c in result.comparisons:
            if c.left_path and c.right_path:
                assert c.content_hash_left is not None
                assert c.content_hash_right is not None


class TestParallelTextPipeline:
    """Verify parallel text pipeline produces correct results."""

    def test_parallel_text_matches_serial(self, tmp_path: Path) -> None:
        left, right = _make_mixed_dirs(tmp_path)
        serial = Comparator(DiffDepth.text, max_workers=1).compare(left, right)
        parallel = Comparator(DiffDepth.text, max_workers=4).compare(left, right)
        assert serial.comparisons == parallel.comparisons
        assert serial.stats == parallel.stats

    def test_parallel_text_preserves_hunks(self, tmp_path: Path) -> None:
        left, right = _make_mixed_dirs(tmp_path)
        result = Comparator(DiffDepth.text, max_workers=4).compare(left, right)
        for c in result.comparisons:
            if c.status == FileStatus.modified:
                assert len(c.hunks) >= 1
                assert c.similarity is not None
                assert c.similarity < 1.0

    def test_parallel_text_preserves_order(self, tmp_path: Path) -> None:
        left, right = _make_mixed_dirs(tmp_path, num_paired=20)
        result = Comparator(DiffDepth.text, max_workers=4).compare(left, right)
        paths = [c.relative_path for c in result.comparisons]
        assert paths == sorted(paths)


class TestParallelErrorHandling:
    """Verify exceptions propagate from worker threads."""

    def test_file_deleted_between_scan_and_compare(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        left_file = left / "vanish.txt"
        right_file = right / "vanish.txt"
        left_file.write_text("will vanish\n")
        right_file.write_text("will vanish\n")

        # Also create extra files to ensure we go through the executor path
        for i in range(5):
            (left / f"pad_{i}.txt").write_text(f"pad {i}\n")
            (right / f"pad_{i}.txt").write_text(f"pad {i}\n")

        # Delete after structure scan but before content compare
        original_compare = Comparator._run_parallel

        def patched_run_parallel(
            self: Comparator,
            structure_comparisons: tuple,  # type: ignore[type-arg]
            compare_fn: object,
        ) -> tuple:  # type: ignore[type-arg]
            left_file.unlink()
            return original_compare(self, structure_comparisons, compare_fn)  # type: ignore[arg-type]

        with (
            patch.object(Comparator, "_run_parallel", patched_run_parallel),
            pytest.raises(FileNotFoundError),
        ):
            Comparator(DiffDepth.content, max_workers=4).compare(left, right)


class TestParallelSingleFilePair:
    """Verify single-file shortcut is unaffected by max_workers."""

    def test_single_file_pair_uses_shortcut(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello\n")
        f2.write_text("world\n")

        with patch("deep_diff.core.comparator.StructureComparator") as mock_structure:
            result = Comparator(DiffDepth.content, max_workers=4).compare(f1, f2)
            mock_structure.assert_not_called()
        assert len(result.comparisons) == 1
        assert result.comparisons[0].status == FileStatus.modified
