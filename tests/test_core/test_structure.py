"""Tests for deep_diff.core.structure."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from deep_diff.core.filtering import FilterConfig
from deep_diff.core.models import FileStatus
from deep_diff.core.structure import StructureComparator


class TestStructureComparatorInit:
    """Verify constructor behavior."""

    def test_default_config(self) -> None:
        comp = StructureComparator()
        assert comp._filter is not None

    def test_custom_config(self) -> None:
        config = FilterConfig(respect_gitignore=False, include_hidden=True)
        comp = StructureComparator(config)
        assert comp._filter._config is config

    def test_none_config_uses_defaults(self) -> None:
        comp = StructureComparator(None)
        assert comp._filter._config == FilterConfig()


class TestStructureComparatorIdentical:
    """Both directories have the same files."""

    def test_identical_flat_directories(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "a.txt").write_text("hello\n")
        (right / "a.txt").write_text("hello\n")
        (left / "b.txt").write_text("world\n")
        (right / "b.txt").write_text("world\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 2
        assert all(c.status == FileStatus.identical for c in result)

    def test_identical_nested_directories(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "sub").mkdir()
        (right / "sub").mkdir()
        (left / "sub" / "file.txt").write_text("nested\n")
        (right / "sub" / "file.txt").write_text("nested\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 1
        assert result[0].relative_path == "sub/file.txt"
        assert result[0].status == FileStatus.identical

    def test_identical_single_file(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "only.txt").write_text("x\n")
        (right / "only.txt").write_text("y\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 1
        assert result[0].status == FileStatus.identical


class TestStructureComparatorLeftOnly:
    """Files only in the left directory."""

    def test_left_only_files(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "orphan.txt").write_text("left\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 1
        assert result[0].status == FileStatus.removed
        assert result[0].left_path == left / "orphan.txt"
        assert result[0].right_path is None

    def test_left_only_nested(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "deep").mkdir()
        (left / "deep" / "nested.txt").write_text("deep\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 1
        assert result[0].relative_path == "deep/nested.txt"
        assert result[0].status == FileStatus.removed


class TestStructureComparatorRightOnly:
    """Files only in the right directory."""

    def test_right_only_files(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (right / "new.txt").write_text("right\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 1
        assert result[0].status == FileStatus.added
        assert result[0].left_path is None
        assert result[0].right_path == right / "new.txt"

    def test_right_only_nested(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (right / "deep").mkdir()
        (right / "deep" / "nested.txt").write_text("deep\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 1
        assert result[0].relative_path == "deep/nested.txt"
        assert result[0].status == FileStatus.added


class TestStructureComparatorMixed:
    """Combination of common and unique files."""

    def test_mixed_with_sample_dirs(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        comp = StructureComparator(FilterConfig(respect_gitignore=False))
        result = comp.compare(left, right)

        by_path = {c.relative_path: c for c in result}

        # Common files → identical (structure only checks existence)
        assert by_path["common.txt"].status == FileStatus.identical
        assert by_path["modified.txt"].status == FileStatus.identical
        assert by_path["sub/nested.txt"].status == FileStatus.identical

        # Left-only → removed
        assert by_path["left_only.txt"].status == FileStatus.removed
        assert by_path["sub/left_nested.txt"].status == FileStatus.removed

        # Right-only → added
        assert by_path["right_only.txt"].status == FileStatus.added
        assert by_path["sub/right_nested.txt"].status == FileStatus.added

    def test_results_sorted_by_relative_path(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        comp = StructureComparator(FilterConfig(respect_gitignore=False))
        result = comp.compare(left, right)

        paths = [c.relative_path for c in result]
        assert paths == sorted(paths)

    def test_results_are_tuple(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)
        assert isinstance(result, tuple)

    def test_results_are_frozen(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)
        assert len(result) > 0
        with pytest.raises(FrozenInstanceError):
            result[0].status = FileStatus.modified  # type: ignore[misc]


class TestStructureComparatorEmptyDirs:
    """Edge cases with empty directories."""

    def test_both_empty(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)
        assert result == ()

    def test_left_empty_right_has_files(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (right / "file.txt").write_text("data\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 1
        assert result[0].status == FileStatus.added

    def test_right_empty_left_has_files(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "file.txt").write_text("data\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert len(result) == 1
        assert result[0].status == FileStatus.removed


class TestStructureComparatorFiltering:
    """Integration with FilterConfig."""

    def test_hidden_files_excluded_by_default(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        paths = {c.relative_path for c in result}
        assert ".hidden" not in paths

    def test_hidden_files_included_when_configured(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        config = FilterConfig(respect_gitignore=False, include_hidden=True)
        result = StructureComparator(config).compare(left, right)

        paths = {c.relative_path for c in result}
        assert ".hidden" in paths

    def test_gitignore_respected(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / ".gitignore").write_text("*.pyc\n")
        (right / ".gitignore").write_text("*.pyc\n")
        (left / "keep.py").write_text("keep\n")
        (right / "keep.py").write_text("keep\n")
        (left / "ignore.pyc").write_text("cache\n")
        (right / "ignore.pyc").write_text("cache\n")

        result = StructureComparator().compare(left, right)

        paths = {c.relative_path for c in result}
        assert "keep.py" in paths
        assert "ignore.pyc" not in paths

    def test_gitignore_disabled(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / ".gitignore").write_text("*.pyc\n")
        (right / ".gitignore").write_text("*.pyc\n")
        (left / "keep.py").write_text("keep\n")
        (right / "keep.py").write_text("keep\n")
        (left / "ignore.pyc").write_text("cache\n")
        (right / "ignore.pyc").write_text("cache\n")

        config = FilterConfig(respect_gitignore=False)
        result = StructureComparator(config).compare(left, right)

        paths = {c.relative_path for c in result}
        assert "ignore.pyc" in paths

    def test_include_patterns(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "code.py").write_text("python\n")
        (right / "code.py").write_text("python\n")
        (left / "data.csv").write_text("csv\n")
        (right / "data.csv").write_text("csv\n")

        config = FilterConfig(respect_gitignore=False, include_patterns=("*.py",))
        result = StructureComparator(config).compare(left, right)

        paths = {c.relative_path for c in result}
        assert "code.py" in paths
        assert "data.csv" not in paths

    def test_exclude_patterns(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "code.py").write_text("python\n")
        (right / "code.py").write_text("python\n")
        (left / "debug.log").write_text("log\n")
        (right / "debug.log").write_text("log\n")

        config = FilterConfig(respect_gitignore=False, exclude_patterns=("*.log",))
        result = StructureComparator(config).compare(left, right)

        paths = {c.relative_path for c in result}
        assert "code.py" in paths
        assert "debug.log" not in paths


class TestStructureComparatorPaths:
    """Path correctness on FileComparison objects."""

    def test_left_path_is_absolute_for_common(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "file.txt").write_text("a\n")
        (right / "file.txt").write_text("b\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert result[0].left_path == left / "file.txt"
        assert result[0].right_path == right / "file.txt"

    def test_left_path_none_for_added(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (right / "new.txt").write_text("new\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert result[0].left_path is None
        assert result[0].right_path is not None

    def test_right_path_none_for_removed(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "old.txt").write_text("old\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert result[0].right_path is None
        assert result[0].left_path is not None

    def test_relative_path_uses_posix_separator(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "sub").mkdir()
        (right / "sub").mkdir()
        (left / "sub" / "file.txt").write_text("a\n")
        (right / "sub" / "file.txt").write_text("b\n")

        result = StructureComparator(FilterConfig(respect_gitignore=False)).compare(left, right)

        assert "/" in result[0].relative_path
        assert "\\" not in result[0].relative_path


class TestStructureComparatorErrors:
    """Error handling: NotADirectoryError propagation."""

    def test_nonexistent_left_raises(self, tmp_path: Path) -> None:
        right = tmp_path / "right"
        right.mkdir()

        with pytest.raises(NotADirectoryError):
            StructureComparator().compare(tmp_path / "nonexistent", right)

    def test_nonexistent_right_raises(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        left.mkdir()

        with pytest.raises(NotADirectoryError):
            StructureComparator().compare(left, tmp_path / "nonexistent")

    def test_file_as_left_raises(self, tmp_path: Path) -> None:
        left_file = tmp_path / "file.txt"
        left_file.write_text("not a dir\n")
        right = tmp_path / "right"
        right.mkdir()

        with pytest.raises(NotADirectoryError):
            StructureComparator().compare(left_file, right)

    def test_file_as_right_raises(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        left.mkdir()
        right_file = tmp_path / "file.txt"
        right_file.write_text("not a dir\n")

        with pytest.raises(NotADirectoryError):
            StructureComparator().compare(left, right_file)
