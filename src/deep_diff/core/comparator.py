"""Comparison orchestrator that chains the layered pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deep_diff.core.filtering import FilterConfig
from deep_diff.core.models import DiffDepth, DiffResult, DiffStats
from deep_diff.core.structure import StructureComparator

if TYPE_CHECKING:
    from pathlib import Path

    from deep_diff.core.models import FileComparison


class Comparator:
    """Orchestrates the comparison pipeline.

    Chains: FilterConfig -> StructureComparator (-> ContentComparator -> TextComparator)
    based on the requested depth level.

    When depth is None, auto-detection is used:
    - Two directories -> structure
    - Two files -> text
    - Mixed (file + dir) -> raises ValueError
    """

    def __init__(
        self,
        depth: DiffDepth | None = None,
        *,
        filter_config: FilterConfig | None = None,
        context_lines: int = 3,
        hash_algo: str = "sha256",
    ) -> None:
        """Initialize the comparator.

        Args:
            depth: Comparison depth level. Auto-detected if None.
            filter_config: Filtering rules. Defaults to FilterConfig() if None.
            context_lines: Number of context lines for text diffs.
            hash_algo: Hash algorithm for content comparison.
        """
        self._depth = depth
        self._filter_config = filter_config or FilterConfig()
        self._context_lines = context_lines
        self._hash_algo = hash_algo

    def compare(self, left: Path, right: Path) -> DiffResult:
        """Run the comparison pipeline.

        Args:
            left: Left path (file or directory).
            right: Right path (file or directory).

        Returns:
            DiffResult with comparisons and stats.

        Raises:
            FileNotFoundError: If left or right does not exist.
            ValueError: If paths are mixed types (one file, one dir).
        """
        left = left.resolve()
        right = right.resolve()

        self._validate_paths_exist(left, right)
        depth = self._resolve_depth(left, right)
        comparisons = self._run_pipeline(left, right, depth)
        stats = DiffStats.from_comparisons(comparisons)

        return DiffResult(
            left_root=left,
            right_root=right,
            depth=depth,
            comparisons=comparisons,
            stats=stats,
        )

    def _resolve_depth(self, left: Path, right: Path) -> DiffDepth:
        """Resolve depth via explicit setting or auto-detection."""
        if self._depth is not None:
            return self._depth

        left_is_dir = left.is_dir()
        right_is_dir = right.is_dir()

        if left_is_dir and right_is_dir:
            return DiffDepth.structure
        if not left_is_dir and not right_is_dir:
            return DiffDepth.text

        msg = (
            "Cannot compare a file with a directory. "
            f"Left ({'directory' if left_is_dir else 'file'}): {left}, "
            f"Right ({'directory' if right_is_dir else 'file'}): {right}"
        )
        raise ValueError(msg)

    def _run_pipeline(
        self,
        left: Path,
        right: Path,
        depth: DiffDepth,
    ) -> tuple[FileComparison, ...]:
        """Execute the comparison pipeline for the given depth."""
        if depth == DiffDepth.structure:
            return StructureComparator(self._filter_config).compare(left, right)

        if depth == DiffDepth.content:
            return self._run_content_pipeline(left, right)

        if depth == DiffDepth.text:
            return self._run_text_pipeline(left, right)

        msg = f"Depth '{depth}' is not yet implemented"
        raise NotImplementedError(msg)

    def _run_content_pipeline(
        self,
        left: Path,
        right: Path,
    ) -> tuple[FileComparison, ...]:
        """Run structure pass, then enrich with content hashes.

        For file pairs, skips the structure pass and hashes directly.
        """
        from deep_diff.core.content import ContentComparator

        content_comp = ContentComparator(hash_algo=self._hash_algo)

        if left.is_file() and right.is_file():
            return (content_comp.compare(left, right),)

        structure_comparisons = StructureComparator(
            self._filter_config,
        ).compare(left, right)

        enriched: list[FileComparison] = []
        for fc in structure_comparisons:
            if fc.left_path and fc.right_path:
                enriched.append(
                    content_comp.compare(
                        fc.left_path,
                        fc.right_path,
                        relative_path=fc.relative_path,
                    )
                )
            else:
                enriched.append(fc)

        return tuple(enriched)

    def _run_text_pipeline(
        self,
        left: Path,
        right: Path,
    ) -> tuple[FileComparison, ...]:
        """Run structure pass, then enrich with text diffs.

        For file pairs, skips the structure pass and diffs directly.
        """
        from deep_diff.core.text import TextComparator

        text_comp = TextComparator(context_lines=self._context_lines)

        if left.is_file() and right.is_file():
            return (text_comp.compare(left, right),)

        structure_comparisons = StructureComparator(
            self._filter_config,
        ).compare(left, right)

        enriched: list[FileComparison] = []
        for fc in structure_comparisons:
            if fc.left_path and fc.right_path:
                enriched.append(
                    text_comp.compare(
                        fc.left_path,
                        fc.right_path,
                        relative_path=fc.relative_path,
                    )
                )
            else:
                enriched.append(fc)

        return tuple(enriched)

    @staticmethod
    def _validate_paths_exist(left: Path, right: Path) -> None:
        """Validate that both paths exist."""
        if not left.exists():
            msg = f"Left path does not exist: {left}"
            raise FileNotFoundError(msg)
        if not right.exists():
            msg = f"Right path does not exist: {right}"
            raise FileNotFoundError(msg)
