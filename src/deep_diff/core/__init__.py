"""Public API for deep_diff.core."""

from __future__ import annotations

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

__all__ = [
    "ChangeType",
    "DiffDepth",
    "DiffResult",
    "DiffStats",
    "FileComparison",
    "FileStatus",
    "Hunk",
    "OutputMode",
    "TextChange",
]
