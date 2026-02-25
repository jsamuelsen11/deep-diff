"""Tests for deep_diff.core.models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from deep_diff.core.models import (
    ChangeType,
    DiffDepth,
    DiffResult,
    DiffStats,
    FileComparison,
    FileStatus,
    Hunk,
    OutputMode,
    TextChange,
)


class TestEnums:
    """Verify enum values and StrEnum string behavior."""

    def test_diff_depth_values(self) -> None:
        assert DiffDepth.structure == "structure"
        assert DiffDepth.content == "content"
        assert DiffDepth.text == "text"
        assert len(DiffDepth) == 3

    def test_output_mode_values(self) -> None:
        assert OutputMode.rich == "rich"
        assert OutputMode.tui == "tui"
        assert OutputMode.json == "json"
        assert OutputMode.html == "html"
        assert len(OutputMode) == 4

    def test_file_status_values(self) -> None:
        assert FileStatus.identical == "identical"
        assert FileStatus.modified == "modified"
        assert FileStatus.added == "added"
        assert FileStatus.removed == "removed"
        assert len(FileStatus) == 4

    def test_change_type_values(self) -> None:
        assert ChangeType.insert == "insert"
        assert ChangeType.delete == "delete"
        assert ChangeType.substitute == "substitute"
        assert ChangeType.equal == "equal"
        assert len(ChangeType) == 4

    def test_str_enum_is_string_comparable(self) -> None:
        assert DiffDepth.structure == "structure"
        assert str(ChangeType.insert) == "insert"
        assert OutputMode.json.value == "json"
        assert f"status: {FileStatus.modified}" == "status: modified"


class TestTextChange:
    """Verify TextChange frozen dataclass."""

    def test_construction(self) -> None:
        tc = TextChange(
            change_type=ChangeType.insert,
            content="new line",
            line_left=None,
            line_right=5,
        )
        assert tc.change_type == ChangeType.insert
        assert tc.content == "new line"
        assert tc.line_left is None
        assert tc.line_right == 5

    def test_frozen_immutable(self) -> None:
        tc = TextChange(
            change_type=ChangeType.delete,
            content="old line",
            line_left=3,
            line_right=None,
        )
        with pytest.raises(FrozenInstanceError):
            tc.content = "changed"  # type: ignore[misc]

    def test_line_numbers_can_be_none(self) -> None:
        tc = TextChange(
            change_type=ChangeType.equal,
            content="same",
            line_left=None,
            line_right=None,
        )
        assert tc.line_left is None
        assert tc.line_right is None


class TestHunk:
    """Verify Hunk frozen dataclass."""

    def test_construction(self) -> None:
        change = TextChange(ChangeType.equal, "line", 1, 1)
        hunk = Hunk(
            start_left=1,
            count_left=1,
            start_right=1,
            count_right=1,
            changes=(change,),
        )
        assert hunk.start_left == 1
        assert hunk.changes == (change,)

    def test_frozen_immutable(self) -> None:
        hunk = Hunk(start_left=1, count_left=1, start_right=1, count_right=1, changes=())
        with pytest.raises(FrozenInstanceError):
            hunk.start_left = 99  # type: ignore[misc]

    def test_empty_changes(self) -> None:
        hunk = Hunk(start_left=0, count_left=0, start_right=0, count_right=0, changes=())
        assert hunk.changes == ()


class TestFileComparison:
    """Verify FileComparison frozen dataclass."""

    def test_construction_full(self) -> None:
        hunk = Hunk(start_left=1, count_left=1, start_right=1, count_right=1, changes=())
        fc = FileComparison(
            relative_path="file.txt",
            status=FileStatus.modified,
            left_path=Path("/left/file.txt"),
            right_path=Path("/right/file.txt"),
            hunks=(hunk,),
            content_hash_left="abc123",
            content_hash_right="def456",
        )
        assert fc.relative_path == "file.txt"
        assert fc.status == FileStatus.modified
        assert fc.left_path == Path("/left/file.txt")
        assert fc.hunks == (hunk,)
        assert fc.content_hash_left == "abc123"

    def test_construction_defaults(self) -> None:
        fc = FileComparison(
            relative_path="a.txt",
            status=FileStatus.identical,
            left_path=Path("/l/a.txt"),
            right_path=Path("/r/a.txt"),
        )
        assert fc.hunks == ()
        assert fc.content_hash_left is None
        assert fc.content_hash_right is None

    def test_frozen_immutable(self) -> None:
        fc = FileComparison(
            relative_path="a.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/r/a.txt"),
        )
        with pytest.raises(FrozenInstanceError):
            fc.status = FileStatus.removed  # type: ignore[misc]

    def test_paths_can_be_none(self) -> None:
        fc_added = FileComparison("new.txt", FileStatus.added, None, Path("/r/new.txt"))
        assert fc_added.left_path is None

        fc_removed = FileComparison("old.txt", FileStatus.removed, Path("/l/old.txt"), None)
        assert fc_removed.right_path is None


class TestDiffStats:
    """Verify DiffStats frozen dataclass and factory method."""

    def test_construction_direct(self) -> None:
        stats = DiffStats(total_files=10, identical=5, modified=2, added=2, removed=1)
        assert stats.total_files == 10
        assert stats.identical == 5

    def test_from_comparisons_mixed(self) -> None:
        left = Path("/left")
        right = Path("/right")
        comparisons = [
            FileComparison("a.txt", FileStatus.identical, left / "a.txt", right / "a.txt"),
            FileComparison("b.txt", FileStatus.modified, left / "b.txt", right / "b.txt"),
            FileComparison("c.txt", FileStatus.added, None, right / "c.txt"),
            FileComparison("d.txt", FileStatus.removed, left / "d.txt", None),
            FileComparison("e.txt", FileStatus.modified, left / "e.txt", right / "e.txt"),
        ]
        stats = DiffStats.from_comparisons(comparisons)
        assert stats.total_files == 5
        assert stats.identical == 1
        assert stats.modified == 2
        assert stats.added == 1
        assert stats.removed == 1

    def test_from_comparisons_empty(self) -> None:
        stats = DiffStats.from_comparisons([])
        assert stats.total_files == 0
        assert stats.identical == 0
        assert stats.modified == 0
        assert stats.added == 0
        assert stats.removed == 0

    def test_from_comparisons_all_identical(self) -> None:
        left = Path("/left")
        right = Path("/right")
        comparisons = [
            FileComparison("a.txt", FileStatus.identical, left / "a.txt", right / "a.txt"),
            FileComparison("b.txt", FileStatus.identical, left / "b.txt", right / "b.txt"),
        ]
        stats = DiffStats.from_comparisons(comparisons)
        assert stats.total_files == 2
        assert stats.identical == 2
        assert stats.modified == 0
        assert stats.added == 0
        assert stats.removed == 0

    def test_frozen_immutable(self) -> None:
        stats = DiffStats(total_files=1, identical=1, modified=0, added=0, removed=0)
        with pytest.raises(FrozenInstanceError):
            stats.total_files = 99  # type: ignore[misc]


class TestDiffResult:
    """Verify DiffResult frozen dataclass."""

    def test_construction(self) -> None:
        left = Path("/left")
        right = Path("/right")
        fc = FileComparison("a.txt", FileStatus.identical, left / "a.txt", right / "a.txt")
        stats = DiffStats(total_files=1, identical=1, modified=0, added=0, removed=0)
        result = DiffResult(
            left_root=left,
            right_root=right,
            depth=DiffDepth.structure,
            comparisons=(fc,),
            stats=stats,
        )
        assert result.left_root == left
        assert result.depth == DiffDepth.structure
        assert len(result.comparisons) == 1

    def test_frozen_immutable(self) -> None:
        stats = DiffStats(total_files=0, identical=0, modified=0, added=0, removed=0)
        result = DiffResult(
            left_root=Path("/l"),
            right_root=Path("/r"),
            depth=DiffDepth.text,
            comparisons=(),
            stats=stats,
        )
        with pytest.raises(FrozenInstanceError):
            result.depth = DiffDepth.content  # type: ignore[misc]

    def test_empty_comparisons(self) -> None:
        stats = DiffStats(total_files=0, identical=0, modified=0, added=0, removed=0)
        result = DiffResult(
            left_root=Path("/l"),
            right_root=Path("/r"),
            depth=DiffDepth.content,
            comparisons=(),
            stats=stats,
        )
        assert result.comparisons == ()
        assert result.stats.total_files == 0
