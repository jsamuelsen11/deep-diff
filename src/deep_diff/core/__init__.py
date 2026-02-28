"""Public API for deep_diff.core."""

from __future__ import annotations

from deep_diff.core.comparator import Comparator
from deep_diff.core.content import ContentComparator
from deep_diff.core.filtering import FileFilter, FilterConfig
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
from deep_diff.core.structure import StructureComparator
from deep_diff.core.text import TextComparator

__all__ = [
    "ChangeType",
    "Comparator",
    "ContentComparator",
    "DiffDepth",
    "DiffResult",
    "DiffStats",
    "FileComparison",
    "FileFilter",
    "FileStatus",
    "FilterConfig",
    "Hunk",
    "OutputMode",
    "StructureComparator",
    "TextChange",
    "TextComparator",
]
