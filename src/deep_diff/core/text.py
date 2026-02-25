"""Text diff engine using difflib."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

from deep_diff.core.models import (
    ChangeType,
    FileComparison,
    FileStatus,
    Hunk,
    TextChange,
)

if TYPE_CHECKING:
    from pathlib import Path

_BINARY_SAMPLE_BYTES = 8192


class TextComparator:
    """Produces line-level diff hunks for modified text files.

    Compares two files using difflib.SequenceMatcher. Binary files are
    detected via null-byte check and compared for byte equality only
    (no line-level hunks). Text files are decoded as UTF-8 and diffed
    with configurable context lines.
    """

    def __init__(
        self,
        *,
        context_lines: int = 3,
        encoding: str = "utf-8",
        errors: str = "replace",
    ) -> None:
        """Initialize with diff context configuration.

        Args:
            context_lines: Number of unchanged context lines around each
                change in the produced hunks. Defaults to 3.
            encoding: Text encoding used to decode file bytes.
                Defaults to ``"utf-8"``.
            errors: Error handling strategy passed to :meth:`bytes.decode`.
                Defaults to ``"replace"``.  Use ``"strict"`` to raise on
                invalid byte sequences.
        """
        self._context_lines = context_lines
        self._encoding = encoding
        self._errors = errors

    def compare(
        self,
        left: Path,
        right: Path,
        *,
        relative_path: str = "",
    ) -> FileComparison:
        """Compare two files and produce line-level diff hunks.

        Args:
            left: Path to the left file.
            right: Path to the right file.
            relative_path: Relative path label for the result.
                Defaults to ``left.name`` when empty.

        Returns:
            A FileComparison with status, hunks, and similarity.
        """
        if not relative_path:
            relative_path = left.name

        left_bytes = left.read_bytes()
        right_bytes = right.read_bytes()

        if self._is_binary(left_bytes) or self._is_binary(right_bytes):
            return self._compare_binary(
                left_bytes,
                right_bytes,
                relative_path=relative_path,
                left_path=left,
                right_path=right,
            )

        return self._compare_text(
            left_bytes,
            right_bytes,
            relative_path=relative_path,
            left_path=left,
            right_path=right,
        )

    @staticmethod
    def _is_binary(data: bytes) -> bool:
        """Detect binary content via null-byte check."""
        return b"\x00" in data[:_BINARY_SAMPLE_BYTES]

    @staticmethod
    def _compare_binary(
        left_bytes: bytes,
        right_bytes: bytes,
        *,
        relative_path: str,
        left_path: Path,
        right_path: Path,
    ) -> FileComparison:
        """Compare two binary files by byte equality."""
        if left_bytes == right_bytes:
            return FileComparison(
                relative_path=relative_path,
                status=FileStatus.identical,
                left_path=left_path,
                right_path=right_path,
                similarity=1.0,
            )
        return FileComparison(
            relative_path=relative_path,
            status=FileStatus.modified,
            left_path=left_path,
            right_path=right_path,
            similarity=None,
        )

    def _compare_text(
        self,
        left_bytes: bytes,
        right_bytes: bytes,
        *,
        relative_path: str,
        left_path: Path,
        right_path: Path,
    ) -> FileComparison:
        """Compare two text files using difflib.SequenceMatcher."""
        left_text = left_bytes.decode(self._encoding, errors=self._errors)
        right_text = right_bytes.decode(self._encoding, errors=self._errors)

        left_lines = left_text.splitlines(keepends=True)
        right_lines = right_text.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, left_lines, right_lines)
        similarity = matcher.ratio()

        if similarity == 1.0:
            return FileComparison(
                relative_path=relative_path,
                status=FileStatus.identical,
                left_path=left_path,
                right_path=right_path,
                similarity=1.0,
            )

        hunks = self._build_hunks(matcher, left_lines, right_lines)
        return FileComparison(
            relative_path=relative_path,
            status=FileStatus.modified,
            left_path=left_path,
            right_path=right_path,
            hunks=hunks,
            similarity=similarity,
        )

    def _build_hunks(
        self,
        matcher: difflib.SequenceMatcher[str],
        left_lines: list[str],
        right_lines: list[str],
    ) -> tuple[Hunk, ...]:
        """Build Hunk objects from SequenceMatcher grouped opcodes."""
        hunks: list[Hunk] = []

        for group in matcher.get_grouped_opcodes(n=self._context_lines):
            first = group[0]
            last = group[-1]
            start_left = first[1] + 1
            count_left = last[2] - first[1]
            start_right = first[3] + 1
            count_right = last[4] - first[3]

            changes = self._build_changes(group, left_lines, right_lines)

            hunks.append(
                Hunk(
                    start_left=start_left,
                    count_left=count_left,
                    start_right=start_right,
                    count_right=count_right,
                    changes=tuple(changes),
                )
            )

        return tuple(hunks)

    @staticmethod
    def _build_changes(
        group: list[tuple[str, int, int, int, int]],
        left_lines: list[str],
        right_lines: list[str],
    ) -> list[TextChange]:
        """Convert a group of opcodes into TextChange entries."""
        changes: list[TextChange] = []

        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for idx, line in enumerate(left_lines[i1:i2]):
                    changes.append(
                        TextChange(
                            change_type=ChangeType.equal,
                            content=line,
                            line_left=i1 + idx + 1,
                            line_right=j1 + idx + 1,
                        )
                    )
            elif tag == "delete":
                for idx, line in enumerate(left_lines[i1:i2]):
                    changes.append(
                        TextChange(
                            change_type=ChangeType.delete,
                            content=line,
                            line_left=i1 + idx + 1,
                            line_right=None,
                        )
                    )
            elif tag == "insert":
                for idx, line in enumerate(right_lines[j1:j2]):
                    changes.append(
                        TextChange(
                            change_type=ChangeType.insert,
                            content=line,
                            line_left=None,
                            line_right=j1 + idx + 1,
                        )
                    )
            elif tag == "replace":
                for idx, line in enumerate(left_lines[i1:i2]):
                    changes.append(
                        TextChange(
                            change_type=ChangeType.delete,
                            content=line,
                            line_left=i1 + idx + 1,
                            line_right=None,
                        )
                    )
                for idx, line in enumerate(right_lines[j1:j2]):
                    changes.append(
                        TextChange(
                            change_type=ChangeType.insert,
                            content=line,
                            line_left=None,
                            line_right=j1 + idx + 1,
                        )
                    )

        return changes
