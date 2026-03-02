"""Shared utilities for building diff hunks from line sequences."""

from __future__ import annotations

import difflib

from deep_diff.core.models import ChangeType, Hunk, TextChange


def build_hunks_from_lines(
    left_lines: list[str],
    right_lines: list[str],
    *,
    context_lines: int = 3,
) -> tuple[float, tuple[Hunk, ...]]:
    """Build diff hunks from two sequences of lines.

    Uses :class:`difflib.SequenceMatcher` to produce grouped opcodes
    and converts them into :class:`Hunk` / :class:`TextChange` objects.

    Args:
        left_lines: Lines from the left file (with line endings).
        right_lines: Lines from the right file (with line endings).
        context_lines: Number of unchanged context lines around each
            change in the produced hunks.

    Returns:
        A ``(similarity, hunks)`` tuple where *similarity* is the
        :meth:`~difflib.SequenceMatcher.ratio` (0.0-1.0) and *hunks*
        is a tuple of :class:`Hunk` objects.
    """
    matcher = difflib.SequenceMatcher(None, left_lines, right_lines)
    similarity = matcher.ratio()

    if similarity == 1.0:
        return similarity, ()

    hunks: list[Hunk] = []

    for group in matcher.get_grouped_opcodes(n=context_lines):
        first = group[0]
        last = group[-1]

        changes = _build_changes(group, left_lines, right_lines)

        hunks.append(
            Hunk(
                start_left=first[1] + 1,
                count_left=last[2] - first[1],
                start_right=first[3] + 1,
                count_right=last[4] - first[3],
                changes=tuple(changes),
            )
        )

    return similarity, tuple(hunks)


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
