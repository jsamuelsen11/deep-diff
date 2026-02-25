"""Data models for deep-diff comparison results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


class DiffDepth(StrEnum):
    """Comparison depth level."""

    structure = "structure"
    content = "content"
    text = "text"


class OutputMode(StrEnum):
    """Output format for rendering results."""

    rich = "rich"
    tui = "tui"
    json = "json"
    html = "html"


class FileStatus(StrEnum):
    """Status of a file in the comparison."""

    identical = "identical"
    modified = "modified"
    added = "added"
    removed = "removed"


class ChangeType(StrEnum):
    """Type of a text-level change within a hunk."""

    insert = "insert"
    delete = "delete"
    substitute = "substitute"
    equal = "equal"


@dataclass(frozen=True)
class TextChange:
    """A single line-level change within a hunk."""

    change_type: ChangeType
    content: str
    line_left: int | None
    line_right: int | None


@dataclass(frozen=True)
class Hunk:
    """A contiguous block of text changes."""

    start_left: int
    count_left: int
    start_right: int
    count_right: int
    changes: tuple[TextChange, ...]


@dataclass(frozen=True)
class FileComparison:
    """Comparison result for a single file pair."""

    relative_path: str
    status: FileStatus
    left_path: Path | None
    right_path: Path | None
    hunks: tuple[Hunk, ...] = ()
    content_hash_left: str | None = None
    content_hash_right: str | None = None
    similarity: float | None = None


@dataclass(frozen=True)
class DiffStats:
    """Summary statistics for a comparison run."""

    total_files: int
    identical: int
    modified: int
    added: int
    removed: int

    @classmethod
    def from_comparisons(cls, comparisons: Sequence[FileComparison]) -> DiffStats:
        """Compute stats by counting file statuses."""
        return cls(
            total_files=len(comparisons),
            identical=sum(1 for c in comparisons if c.status == FileStatus.identical),
            modified=sum(1 for c in comparisons if c.status == FileStatus.modified),
            added=sum(1 for c in comparisons if c.status == FileStatus.added),
            removed=sum(1 for c in comparisons if c.status == FileStatus.removed),
        )


@dataclass(frozen=True)
class DiffResult:
    """Top-level result of a comparison run."""

    left_root: Path
    right_root: Path
    depth: DiffDepth
    comparisons: tuple[FileComparison, ...]
    stats: DiffStats
