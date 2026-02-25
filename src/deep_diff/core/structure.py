"""Directory structure comparison (file existence only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deep_diff.core.filtering import FileFilter, FilterConfig
from deep_diff.core.models import FileComparison, FileStatus

if TYPE_CHECKING:
    from pathlib import Path


class StructureComparator:
    """Compares two directory trees by file existence only.

    Uses FileFilter to scan both directories, then classifies each
    relative path as identical (present in both), removed (left only),
    or added (right only). Does not inspect file content.
    """

    def __init__(self, config: FilterConfig | None = None) -> None:
        """Initialize with an optional filter configuration.

        Args:
            config: Filtering rules. Defaults to FilterConfig() if None.
        """
        self._filter = FileFilter(config or FilterConfig())

    def compare(self, left: Path, right: Path) -> tuple[FileComparison, ...]:
        """Compare two directory trees by structure.

        Args:
            left: Root of the left directory tree.
            right: Root of the right directory tree.

        Returns:
            Sorted tuple of FileComparison objects.

        Raises:
            NotADirectoryError: If left or right is not a directory.
        """
        left_paths = set(self._filter.scan(left))
        right_paths = set(self._filter.scan(right))

        all_paths = sorted(left_paths | right_paths)

        comparisons: list[FileComparison] = []
        for rel_path in all_paths:
            in_left = rel_path in left_paths
            in_right = rel_path in right_paths

            if in_left and in_right:
                status = FileStatus.identical
                left_full = left / rel_path
                right_full = right / rel_path
            elif in_left:
                status = FileStatus.removed
                left_full = left / rel_path
                right_full = None
            else:
                status = FileStatus.added
                left_full = None
                right_full = right / rel_path

            comparisons.append(
                FileComparison(
                    relative_path=rel_path,
                    status=status,
                    left_path=left_full,
                    right_path=right_full,
                )
            )

        return tuple(comparisons)
