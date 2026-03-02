"""YAML structural diff plugin."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml

from deep_diff.core.diff_utils import build_hunks_from_lines
from deep_diff.core.models import FileComparison, FileStatus

if TYPE_CHECKING:
    from pathlib import Path


class YamlPlugin:
    """Compares YAML files by structure rather than raw text.

    Parses YAML, converts to a canonical JSON representation
    (sorted keys, consistent indent), then diffs the normalized text.
    Key reordering and formatting differences are not reported.

    Falls back to the default TextComparator when YAML parsing fails.
    """

    @property
    def name(self) -> str:
        return "yaml"

    @property
    def extensions(self) -> tuple[str, ...]:
        return (".yaml", ".yml")

    def compare(
        self,
        left: Path,
        right: Path,
        *,
        relative_path: str = "",
        context_lines: int = 3,
    ) -> FileComparison:
        """Compare two YAML files by normalized structure.

        Args:
            left: Path to the left YAML file.
            right: Path to the right YAML file.
            relative_path: Display path label. Defaults to left.name when empty.
            context_lines: Number of context lines around each change.

        Returns:
            A FileComparison with structural diff hunks.
        """
        if not relative_path:
            relative_path = left.name

        left_text = left.read_text(encoding="utf-8")
        right_text = right.read_text(encoding="utf-8")

        try:
            left_obj = yaml.safe_load(left_text)
            right_obj = yaml.safe_load(right_text)
        except yaml.YAMLError:
            return self._text_fallback(
                left, right, relative_path=relative_path, context_lines=context_lines
            )

        if left_obj == right_obj:
            return FileComparison(
                relative_path=relative_path,
                status=FileStatus.identical,
                left_path=left,
                right_path=right,
                similarity=1.0,
            )

        left_normalized = json.dumps(left_obj, sort_keys=True, indent=2, default=str) + "\n"
        right_normalized = json.dumps(right_obj, sort_keys=True, indent=2, default=str) + "\n"

        left_lines = left_normalized.splitlines(keepends=True)
        right_lines = right_normalized.splitlines(keepends=True)
        similarity, hunks = build_hunks_from_lines(
            left_lines, right_lines, context_lines=context_lines
        )

        return FileComparison(
            relative_path=relative_path,
            status=FileStatus.modified,
            left_path=left,
            right_path=right,
            hunks=hunks,
            similarity=similarity,
        )

    @staticmethod
    def _text_fallback(
        left: Path,
        right: Path,
        *,
        relative_path: str,
        context_lines: int,
    ) -> FileComparison:
        """Fall back to raw text diff when YAML parsing fails."""
        from deep_diff.core.text import TextComparator

        return TextComparator(context_lines=context_lines).compare(
            left, right, relative_path=relative_path
        )
