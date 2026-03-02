"""Tests for deep_diff.core.diff_utils."""

from __future__ import annotations

from deep_diff.core.diff_utils import build_hunks_from_lines
from deep_diff.core.models import ChangeType


class TestBuildHunksFromLines:
    """Verify hunk building from line sequences."""

    def test_identical_lines_returns_no_hunks(self) -> None:
        lines = ["hello\n", "world\n"]
        similarity, hunks = build_hunks_from_lines(lines, lines)
        assert similarity == 1.0
        assert hunks == ()

    def test_single_line_change(self) -> None:
        left = ["aaa\n"]
        right = ["bbb\n"]
        similarity, hunks = build_hunks_from_lines(left, right)
        assert similarity < 1.0
        assert len(hunks) == 1
        changes = hunks[0].changes
        # "replace" opcode produces deletes + inserts
        types = [c.change_type for c in changes]
        assert ChangeType.delete in types
        assert ChangeType.insert in types

    def test_insertion_produces_insert_changes(self) -> None:
        left = ["line1\n"]
        right = ["line1\n", "line2\n"]
        similarity, hunks = build_hunks_from_lines(left, right)
        assert similarity < 1.0
        assert len(hunks) >= 1
        insert_changes = [c for c in hunks[0].changes if c.change_type == ChangeType.insert]
        assert len(insert_changes) == 1
        assert insert_changes[0].content == "line2\n"

    def test_deletion_produces_delete_changes(self) -> None:
        left = ["line1\n", "line2\n"]
        right = ["line1\n"]
        similarity, hunks = build_hunks_from_lines(left, right)
        assert similarity < 1.0
        delete_changes = [c for c in hunks[0].changes if c.change_type == ChangeType.delete]
        assert len(delete_changes) == 1
        assert delete_changes[0].content == "line2\n"

    def test_context_lines_controls_surrounding(self) -> None:
        left = [f"line{i}\n" for i in range(20)]
        right = left.copy()
        right[10] = "CHANGED\n"

        _, hunks_0 = build_hunks_from_lines(left, right, context_lines=0)
        _, hunks_5 = build_hunks_from_lines(left, right, context_lines=5)

        # More context lines means more equal lines included
        assert len(hunks_0[0].changes) < len(hunks_5[0].changes)

    def test_hunk_positions_are_one_based(self) -> None:
        left = ["a\n"]
        right = ["b\n"]
        _, hunks = build_hunks_from_lines(left, right)
        assert hunks[0].start_left == 1
        assert hunks[0].start_right == 1

    def test_empty_inputs_return_no_hunks(self) -> None:
        similarity, hunks = build_hunks_from_lines([], [])
        assert similarity == 1.0
        assert hunks == ()

    def test_left_empty_right_nonempty(self) -> None:
        similarity, hunks = build_hunks_from_lines([], ["new\n"])
        assert similarity < 1.0
        assert len(hunks) == 1
        insert_changes = [c for c in hunks[0].changes if c.change_type == ChangeType.insert]
        assert len(insert_changes) == 1

    def test_hunks_are_tuples(self) -> None:
        left = ["a\n"]
        right = ["b\n"]
        _, hunks = build_hunks_from_lines(left, right)
        assert isinstance(hunks, tuple)
        assert isinstance(hunks[0].changes, tuple)

    def test_line_numbers_are_correct(self) -> None:
        left = ["keep\n", "old\n", "keep\n"]
        right = ["keep\n", "new\n", "keep\n"]
        _, hunks = build_hunks_from_lines(left, right, context_lines=0)
        changes = hunks[0].changes
        # The deleted "old" line should be at line_left=2
        deletes = [c for c in changes if c.change_type == ChangeType.delete]
        assert deletes[0].line_left == 2
        assert deletes[0].line_right is None
        # The inserted "new" line should be at line_right=2
        inserts = [c for c in changes if c.change_type == ChangeType.insert]
        assert inserts[0].line_right == 2
        assert inserts[0].line_left is None
