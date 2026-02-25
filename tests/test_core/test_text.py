"""Tests for deep_diff.core.text."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest

from deep_diff.core.models import ChangeType, FileComparison, FileStatus
from deep_diff.core.text import TextComparator

if TYPE_CHECKING:
    from pathlib import Path


class TestTextComparatorInit:
    """Verify constructor behavior."""

    def test_default_context_lines(self) -> None:
        comp = TextComparator()
        assert comp._context_lines == 3

    def test_custom_context_lines(self) -> None:
        comp = TextComparator(context_lines=5)
        assert comp._context_lines == 5

    def test_zero_context_lines(self) -> None:
        comp = TextComparator(context_lines=0)
        assert comp._context_lines == 0

    def test_default_encoding(self) -> None:
        comp = TextComparator()
        assert comp._encoding == "utf-8"

    def test_custom_encoding(self) -> None:
        comp = TextComparator(encoding="latin-1")
        assert comp._encoding == "latin-1"

    def test_default_errors(self) -> None:
        comp = TextComparator()
        assert comp._errors == "replace"

    def test_custom_errors(self) -> None:
        comp = TextComparator(errors="strict")
        assert comp._errors == "strict"


class TestTextComparatorIdentical:
    """Identical files produce no hunks and similarity 1.0."""

    def test_identical_single_line(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("hello\n")
        right.write_text("hello\n")

        result = TextComparator().compare(left, right)

        assert result.status == FileStatus.identical
        assert result.similarity == 1.0
        assert result.hunks == ()

    def test_identical_multiline(self, tmp_path: Path) -> None:
        content = "line 1\nline 2\nline 3\n"
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text(content)
        right.write_text(content)

        result = TextComparator().compare(left, right)

        assert result.status == FileStatus.identical
        assert result.similarity == 1.0
        assert result.hunks == ()

    def test_identical_files_no_hunks(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("same\n")
        right.write_text("same\n")

        result = TextComparator().compare(left, right)
        assert len(result.hunks) == 0


class TestTextComparatorModified:
    """Modified files produce hunks with correct changes."""

    def test_single_line_modification(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)

        assert result.status == FileStatus.modified
        assert len(result.hunks) >= 1

    def test_insertion_at_end(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("line 1\n")
        right.write_text("line 1\nnew line\n")

        result = TextComparator().compare(left, right)

        assert result.status == FileStatus.modified
        insert_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.insert
        ]
        assert len(insert_changes) >= 1
        assert any("new line" in c.content for c in insert_changes)

    def test_deletion_at_end(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("line 1\nold line\n")
        right.write_text("line 1\n")

        result = TextComparator().compare(left, right)

        assert result.status == FileStatus.modified
        delete_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.delete
        ]
        assert len(delete_changes) >= 1

    def test_insertion_at_start(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("existing\n")
        right.write_text("new\nexisting\n")

        result = TextComparator().compare(left, right)

        assert result.status == FileStatus.modified
        insert_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.insert
        ]
        assert len(insert_changes) >= 1

    def test_deletion_at_start(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("old\nexisting\n")
        right.write_text("existing\n")

        result = TextComparator().compare(left, right)

        assert result.status == FileStatus.modified
        delete_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.delete
        ]
        assert len(delete_changes) >= 1

    def test_multiple_hunks_when_changes_far_apart(self, tmp_path: Path) -> None:
        left_lines = [f"line {i}\n" for i in range(20)]
        right_lines = list(left_lines)
        right_lines[2] = "changed 2\n"
        right_lines[17] = "changed 17\n"

        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("".join(left_lines))
        right.write_text("".join(right_lines))

        result = TextComparator(context_lines=3).compare(left, right)

        assert result.status == FileStatus.modified
        assert len(result.hunks) == 2

    def test_hunks_not_empty_for_modified(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)
        assert len(result.hunks) >= 1


class TestTextComparatorHunkStructure:
    """Verify hunk fields and change details."""

    def test_hunk_start_left_is_1indexed(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("old\n")
        right.write_text("new\n")

        result = TextComparator(context_lines=0).compare(left, right)

        assert result.hunks[0].start_left == 1

    def test_hunk_changes_include_equal_for_context(
        self, sample_text_files: tuple[Path, Path]
    ) -> None:
        left, right = sample_text_files
        result = TextComparator(context_lines=3).compare(left, right)

        equal_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.equal
        ]
        assert len(equal_changes) > 0

    def test_insert_change_has_no_left_line(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("a\n")
        right.write_text("a\nb\n")

        result = TextComparator().compare(left, right)

        insert_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.insert
        ]
        assert len(insert_changes) >= 1
        assert all(c.line_left is None for c in insert_changes)

    def test_delete_change_has_no_right_line(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("a\nb\n")
        right.write_text("a\n")

        result = TextComparator().compare(left, right)

        delete_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.delete
        ]
        assert len(delete_changes) >= 1
        assert all(c.line_right is None for c in delete_changes)

    def test_equal_change_has_both_line_numbers(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator(context_lines=3).compare(left, right)

        equal_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.equal
        ]
        assert len(equal_changes) > 0
        assert all(c.line_left is not None for c in equal_changes)
        assert all(c.line_right is not None for c in equal_changes)

    def test_replace_emits_delete_then_insert(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("old line\n")
        right.write_text("new line\n")

        result = TextComparator(context_lines=0).compare(left, right)

        changes = list(result.hunks[0].changes)
        non_equal = [c for c in changes if c.change_type != ChangeType.equal]
        delete_idx = next(i for i, c in enumerate(non_equal) if c.change_type == ChangeType.delete)
        insert_idx = next(i for i, c in enumerate(non_equal) if c.change_type == ChangeType.insert)
        assert delete_idx < insert_idx

    def test_changes_are_tuple(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)
        for hunk in result.hunks:
            assert isinstance(hunk.changes, tuple)


class TestTextComparatorContextLines:
    """Verify context_lines configuration."""

    def test_context_0_no_equal_lines(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("line 1\nline 2\nline 3\n")
        right.write_text("line 1\nchanged\nline 3\n")

        result = TextComparator(context_lines=0).compare(left, right)

        equal_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.equal
        ]
        assert len(equal_changes) == 0

    def test_large_context_merges_all_changes(self, tmp_path: Path) -> None:
        left_lines = [f"line {i}\n" for i in range(20)]
        right_lines = list(left_lines)
        right_lines[2] = "changed 2\n"
        right_lines[17] = "changed 17\n"

        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("".join(left_lines))
        right.write_text("".join(right_lines))

        result = TextComparator(context_lines=100).compare(left, right)

        assert len(result.hunks) == 1

    def test_context_applied_symmetrically(self, tmp_path: Path) -> None:
        lines = [f"line {i}\n" for i in range(10)]
        modified = list(lines)
        modified[5] = "changed\n"

        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("".join(lines))
        right.write_text("".join(modified))

        result = TextComparator(context_lines=2).compare(left, right)

        hunk = result.hunks[0]
        changes = list(hunk.changes)
        non_equal_idx = next(i for i, c in enumerate(changes) if c.change_type != ChangeType.equal)
        equal_before = sum(1 for c in changes[:non_equal_idx] if c.change_type == ChangeType.equal)
        assert equal_before == 2


class TestTextComparatorSimilarity:
    """Verify similarity ratio computation."""

    def test_identical_files_similarity_is_1(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("same\n")
        right.write_text("same\n")

        result = TextComparator().compare(left, right)
        assert result.similarity == 1.0

    def test_completely_different_files_low_similarity(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("alpha\nbeta\ngamma\n")
        right.write_text("one\ntwo\nthree\n")

        result = TextComparator().compare(left, right)
        assert result.similarity is not None
        assert result.similarity < 0.5

    def test_partially_similar_ratio_in_range(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)
        assert result.similarity is not None
        assert 0.0 <= result.similarity <= 1.0

    def test_similarity_is_float_for_modified(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)
        assert isinstance(result.similarity, float)


class TestTextComparatorBinary:
    """Verify binary file detection and handling."""

    def test_binary_file_no_hunks(self, binary_files: tuple[Path, Path]) -> None:
        left, right = binary_files
        result = TextComparator().compare(left, right)
        assert result.hunks == ()

    def test_binary_file_status_is_modified(self, binary_files: tuple[Path, Path]) -> None:
        left, right = binary_files
        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.modified

    def test_identical_binary_files(self, tmp_path: Path) -> None:
        data = b"\x00\x01\x02\x03"
        left = tmp_path / "a.bin"
        right = tmp_path / "b.bin"
        left.write_bytes(data)
        right.write_bytes(data)

        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.identical
        assert result.similarity == 1.0

    def test_binary_modified_similarity_is_none(self, binary_files: tuple[Path, Path]) -> None:
        left, right = binary_files
        result = TextComparator().compare(left, right)
        assert result.similarity is None

    def test_binary_detection_uses_null_byte(self, tmp_path: Path) -> None:
        left = tmp_path / "a.bin"
        right = tmp_path / "b.bin"
        left.write_bytes(b"text with \x00 null")
        right.write_bytes(b"text with \x00 different")

        result = TextComparator().compare(left, right)
        assert result.hunks == ()

    def test_text_file_not_misdetected(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("hello world\n")
        right.write_text("hello changed\n")

        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.modified
        assert len(result.hunks) >= 1


class TestTextComparatorEmpty:
    """Edge cases with empty files."""

    def test_both_empty_files_identical(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("")
        right.write_text("")

        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.identical
        assert result.similarity == 1.0
        assert result.hunks == ()

    def test_empty_left_nonempty_right(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("")
        right.write_text("content\n")

        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.modified
        insert_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.insert
        ]
        assert len(insert_changes) >= 1

    def test_empty_right_nonempty_left(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("content\n")
        right.write_text("")

        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.modified
        delete_changes = [
            c for h in result.hunks for c in h.changes if c.change_type == ChangeType.delete
        ]
        assert len(delete_changes) >= 1


class TestTextComparatorNoTrailingNewline:
    """Files without trailing newline."""

    def test_no_trailing_newline_both_sides(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("old")
        right.write_text("new")

        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.modified
        assert len(result.hunks) >= 1

    def test_newline_difference_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("line\n")
        right.write_text("line")

        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.modified

    def test_no_trailing_newline_identical(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("same")
        right.write_text("same")

        result = TextComparator().compare(left, right)
        assert result.status == FileStatus.identical


class TestTextComparatorEncoding:
    """Verify configurable encoding and error handling."""

    def test_latin1_encoding(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_bytes("caf\xe9\n".encode("latin-1"))
        right.write_bytes("caf\xe9 latte\n".encode("latin-1"))

        result = TextComparator(encoding="latin-1").compare(left, right)
        assert result.status == FileStatus.modified
        assert len(result.hunks) >= 1

    def test_strict_errors_raises_on_invalid_bytes(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_bytes(b"valid utf-8\n")
        right.write_bytes(b"invalid \xff\xfe bytes\n")

        with pytest.raises(UnicodeDecodeError):
            TextComparator(errors="strict").compare(left, right)

    def test_replace_errors_handles_invalid_bytes(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_bytes(b"valid utf-8\n")
        right.write_bytes(b"invalid \xff\xfe bytes\n")

        result = TextComparator(errors="replace").compare(left, right)
        assert result.status == FileStatus.modified


class TestTextComparatorResults:
    """Verify result type and immutability."""

    def test_returns_file_comparison(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)
        assert isinstance(result, FileComparison)

    def test_result_is_frozen(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)
        with pytest.raises(FrozenInstanceError):
            result.status = FileStatus.identical  # type: ignore[misc]

    def test_relative_path_defaults_to_filename(self, tmp_path: Path) -> None:
        left = tmp_path / "myfile.txt"
        right = tmp_path / "other.txt"
        left.write_text("a\n")
        right.write_text("b\n")

        result = TextComparator().compare(left, right)
        assert result.relative_path == "myfile.txt"

    def test_custom_relative_path(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("a\n")
        right.write_text("b\n")

        result = TextComparator().compare(left, right, relative_path="custom/path.txt")
        assert result.relative_path == "custom/path.txt"

    def test_hunks_are_tuple(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)
        assert isinstance(result.hunks, tuple)

    def test_left_and_right_paths_set(self, sample_text_files: tuple[Path, Path]) -> None:
        left, right = sample_text_files
        result = TextComparator().compare(left, right)
        assert result.left_path == left
        assert result.right_path == right
