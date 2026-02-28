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

    def test_default_hash_algo(self) -> None:
        c = Comparator()
        assert c._hash_algo == "sha256"

    def test_custom_hash_algo(self) -> None:
        c = Comparator(hash_algo="md5")
        assert c._hash_algo == "md5"


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
        result = Comparator().compare(f1, f2)
        assert result.depth == DiffDepth.text
        assert len(result.comparisons) == 1
        assert result.comparisons[0].status == FileStatus.modified

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


class TestComparatorContentDepthOnDirs:
    """Verify structure -> content pipeline for directory comparisons."""

    def test_content_depth_on_dirs_returns_result(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.content).compare(left, right)
        assert isinstance(result, DiffResult)
        assert result.depth == DiffDepth.content

    def test_identical_files_have_matching_hashes(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "same.txt").write_text("same content\n")
        (right / "same.txt").write_text("same content\n")

        result = Comparator(DiffDepth.content).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        same = by_path["same.txt"]
        assert same.status == FileStatus.identical
        assert same.content_hash_left == same.content_hash_right
        assert same.similarity == 1.0

    def test_modified_files_have_different_hashes(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "changed.txt").write_text("original\n")
        (right / "changed.txt").write_text("modified\n")

        result = Comparator(DiffDepth.content).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        changed = by_path["changed.txt"]
        assert changed.status == FileStatus.modified
        assert changed.content_hash_left != changed.content_hash_right
        assert changed.similarity is None

    def test_added_files_pass_through(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (right / "new.txt").write_text("added\n")

        result = Comparator(DiffDepth.content).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        added = by_path["new.txt"]
        assert added.status == FileStatus.added
        assert added.left_path is None
        assert added.content_hash_left is None
        assert added.content_hash_right is None

    def test_removed_files_pass_through(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "old.txt").write_text("removed\n")

        result = Comparator(DiffDepth.content).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        removed = by_path["old.txt"]
        assert removed.status == FileStatus.removed
        assert removed.right_path is None
        assert removed.content_hash_left is None
        assert removed.content_hash_right is None

    def test_mixed_statuses_all_correct(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "same.txt").write_text("identical\n")
        (right / "same.txt").write_text("identical\n")
        (left / "changed.txt").write_text("before\n")
        (right / "changed.txt").write_text("after\n")
        (left / "gone.txt").write_text("removed\n")
        (right / "new.txt").write_text("added\n")

        result = Comparator(DiffDepth.content).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        assert by_path["same.txt"].status == FileStatus.identical
        assert by_path["changed.txt"].status == FileStatus.modified
        assert by_path["gone.txt"].status == FileStatus.removed
        assert by_path["new.txt"].status == FileStatus.added
        assert result.stats.identical == 1
        assert result.stats.modified == 1
        assert result.stats.removed == 1
        assert result.stats.added == 1

    def test_content_hashes_populated_for_paired_files(
        self, sample_dirs: tuple[Path, Path]
    ) -> None:
        left, right = sample_dirs
        result = Comparator(DiffDepth.content).compare(left, right)

        for c in result.comparisons:
            if c.left_path and c.right_path:
                assert c.content_hash_left is not None
                assert c.content_hash_right is not None


class TestComparatorContentDepthOnFiles:
    """Verify content pipeline on single file pairs."""

    def test_hash_algo_forwarded_to_content_comparator(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("same\n")
        right.write_text("same\n")

        result = Comparator(DiffDepth.content, hash_algo="md5").compare(left, right)

        fc = result.comparisons[0]
        assert fc.status == FileStatus.identical
        assert fc.content_hash_left is not None
        # MD5 hex digest is 32 chars; SHA-256 would be 64
        assert len(fc.content_hash_left) == 32

    def test_identical_files(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("same\n")
        right.write_text("same\n")

        result = Comparator(DiffDepth.content).compare(left, right)

        assert len(result.comparisons) == 1
        assert result.comparisons[0].status == FileStatus.identical
        assert result.comparisons[0].content_hash_left == result.comparisons[0].content_hash_right

    def test_different_files(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("hello\n")
        right.write_text("world\n")

        result = Comparator(DiffDepth.content).compare(left, right)

        assert len(result.comparisons) == 1
        assert result.comparisons[0].status == FileStatus.modified
        assert result.comparisons[0].content_hash_left != result.comparisons[0].content_hash_right


class TestComparatorTextDepthOnDirs:
    """Verify structure -> text pipeline for directory comparisons."""

    def test_text_depth_on_dirs_returns_result(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "a.txt").write_text("hello\n")
        (right / "a.txt").write_text("hello\n")

        result = Comparator(DiffDepth.text).compare(left, right)
        assert result.depth == DiffDepth.text
        assert len(result.comparisons) == 1

    def test_identical_files_enriched_with_similarity(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "same.txt").write_text("same content\nline 2\n")
        (right / "same.txt").write_text("same content\nline 2\n")

        result = Comparator(DiffDepth.text).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        same = by_path["same.txt"]
        assert same.status == FileStatus.identical
        assert same.similarity == 1.0
        assert same.hunks == ()

    def test_modified_files_get_hunks(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "changed.txt").write_text("original\n")
        (right / "changed.txt").write_text("modified\n")

        result = Comparator(DiffDepth.text).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        changed = by_path["changed.txt"]
        assert changed.status == FileStatus.modified
        assert changed.similarity is not None
        assert changed.similarity < 1.0
        assert len(changed.hunks) >= 1

    def test_added_files_pass_through(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (right / "new.txt").write_text("added\n")

        result = Comparator(DiffDepth.text).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        added = by_path["new.txt"]
        assert added.status == FileStatus.added
        assert added.left_path is None
        assert added.hunks == ()
        assert added.similarity is None

    def test_removed_files_pass_through(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "old.txt").write_text("removed\n")

        result = Comparator(DiffDepth.text).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        removed = by_path["old.txt"]
        assert removed.status == FileStatus.removed
        assert removed.right_path is None
        assert removed.hunks == ()
        assert removed.similarity is None

    def test_mixed_statuses_all_correct(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "same.txt").write_text("identical\n")
        (right / "same.txt").write_text("identical\n")
        (left / "changed.txt").write_text("before\n")
        (right / "changed.txt").write_text("after\n")
        (left / "gone.txt").write_text("removed\n")
        (right / "new.txt").write_text("added\n")

        result = Comparator(DiffDepth.text).compare(left, right)

        by_path = {c.relative_path: c for c in result.comparisons}
        assert by_path["same.txt"].status == FileStatus.identical
        assert by_path["changed.txt"].status == FileStatus.modified
        assert by_path["gone.txt"].status == FileStatus.removed
        assert by_path["new.txt"].status == FileStatus.added
        assert result.stats.identical == 1
        assert result.stats.modified == 1
        assert result.stats.removed == 1
        assert result.stats.added == 1
