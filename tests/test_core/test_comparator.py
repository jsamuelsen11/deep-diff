"""Tests for deep_diff.core.comparator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deep_diff.core.comparator import Comparator
from deep_diff.core.filtering import FilterConfig
from deep_diff.core.models import DiffDepth, DiffResult, DiffStats, FileStatus

if TYPE_CHECKING:
    from pathlib import Path


class TestComparatorInit:
    """Verify Comparator constructor defaults and explicit settings."""

    def test_default_depth_is_none(self) -> None:
        c = Comparator()
        assert c._depth is None

    def test_explicit_depth(self) -> None:
        c = Comparator(DiffDepth.structure)
        assert c._depth == DiffDepth.structure

    def test_default_filter_config(self) -> None:
        c = Comparator()
        assert c._filter_config == FilterConfig()

    def test_custom_filter_config(self) -> None:
        config = FilterConfig(include_hidden=True)
        c = Comparator(filter_config=config)
        assert c._filter_config is config


class TestComparatorAutoDetection:
    """Verify depth auto-detection from path types."""

    def test_two_dirs_auto_detects_structure(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator().compare(left, right)
        assert result.depth == DiffDepth.structure

    def test_two_files_auto_detects_text(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello\n")
        f2.write_text("world\n")
        with pytest.raises(NotImplementedError, match="text"):
            Comparator().compare(f1, f2)

    def test_mixed_file_and_dir_raises(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        a_file = left / "common.txt"
        with pytest.raises(ValueError, match="Cannot compare a file with a directory"):
            Comparator().compare(a_file, right)

    def test_mixed_dir_and_file_raises(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        a_file = right / "common.txt"
        with pytest.raises(ValueError, match="Cannot compare a file with a directory"):
            Comparator().compare(left, a_file)

    def test_explicit_depth_overrides_auto(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        assert result.depth == DiffDepth.structure


class TestComparatorStructureDepth:
    """Verify structure depth pipeline produces correct DiffResult."""

    def test_returns_diff_result(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        assert isinstance(result, DiffResult)

    def test_result_has_resolved_roots(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        assert result.left_root == left.resolve()
        assert result.right_root == right.resolve()

    def test_result_depth_matches(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        assert result.depth == DiffDepth.structure

    def test_stats_match_comparisons(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        expected_stats = DiffStats.from_comparisons(result.comparisons)
        assert result.stats == expected_stats

    def test_comparisons_sorted_by_path(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        paths = [c.relative_path for c in result.comparisons]
        assert paths == sorted(paths)

    def test_filter_config_forwarded(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        config = FilterConfig(include_hidden=True)
        result = Comparator(DiffDepth.structure, filter_config=config).compare(left, right)
        paths = {c.relative_path for c in result.comparisons}
        assert ".hidden" in paths

    def test_hidden_excluded_by_default(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        paths = {c.relative_path for c in result.comparisons}
        assert ".hidden" not in paths

    def test_empty_dirs_produce_empty_result(self, tmp_path: Path) -> None:
        left = tmp_path / "empty_left"
        right = tmp_path / "empty_right"
        left.mkdir()
        right.mkdir()
        result = Comparator(DiffDepth.structure).compare(left, right)
        assert result.comparisons == ()
        assert result.stats.total_files == 0

    def test_structure_classifies_correctly(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        statuses = {c.relative_path: c.status for c in result.comparisons}
        assert statuses["common.txt"] == FileStatus.identical
        assert statuses["left_only.txt"] == FileStatus.removed
        assert statuses["right_only.txt"] == FileStatus.added


class TestComparatorPathValidation:
    """Verify path existence validation."""

    def test_missing_left_raises(self, tmp_path: Path) -> None:
        right = tmp_path / "right"
        right.mkdir()
        missing = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError, match="Left path does not exist"):
            Comparator(DiffDepth.structure).compare(missing, right)

    def test_missing_right_raises(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        left.mkdir()
        missing = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError, match="Right path does not exist"):
            Comparator(DiffDepth.structure).compare(left, missing)

    def test_both_missing_reports_left_first(self, tmp_path: Path) -> None:
        missing_l = tmp_path / "missing_left"
        missing_r = tmp_path / "missing_right"
        with pytest.raises(FileNotFoundError, match="Left path"):
            Comparator(DiffDepth.structure).compare(missing_l, missing_r)

    def test_paths_are_resolved(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.structure).compare(left, right)
        assert result.left_root.is_absolute()
        assert result.right_root.is_absolute()


class TestComparatorNotImplemented:
    """Verify unimplemented depths raise NotImplementedError."""

    def test_content_depth_raises(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        with pytest.raises(NotImplementedError, match="content"):
            Comparator(DiffDepth.content).compare(left, right)

    def test_text_depth_on_dirs_raises(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        with pytest.raises(NotImplementedError, match="text"):
            Comparator(DiffDepth.text).compare(left, right)
