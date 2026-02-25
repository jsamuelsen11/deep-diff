"""Shared test fixtures for deep-diff."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def sample_dirs(tmp_path: Path) -> tuple[Path, Path]:
    """Create two directory trees with known differences.

    Structure:
        left/
            common.txt          (identical in both)
            modified.txt        (different content)
            left_only.txt       (only in left)
            sub/
                nested.txt      (identical in both)
                left_nested.txt (only in left)
            .hidden             (hidden file)
        right/
            common.txt          (identical in both)
            modified.txt        (different content)
            right_only.txt      (only in right)
            sub/
                nested.txt      (identical in both)
                right_nested.txt(only in right)
            .hidden             (hidden file, different content)
    """
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "sub").mkdir()
    (right / "sub").mkdir()

    # Common identical file
    (left / "common.txt").write_text("same content\n")
    (right / "common.txt").write_text("same content\n")

    # Common modified file
    (left / "modified.txt").write_text("original line\n")
    (right / "modified.txt").write_text("changed line\n")

    # Only in left
    (left / "left_only.txt").write_text("left only\n")

    # Only in right
    (right / "right_only.txt").write_text("right only\n")

    # Nested identical
    (left / "sub" / "nested.txt").write_text("nested same\n")
    (right / "sub" / "nested.txt").write_text("nested same\n")

    # Nested only-left / only-right
    (left / "sub" / "left_nested.txt").write_text("left nested\n")
    (right / "sub" / "right_nested.txt").write_text("right nested\n")

    # Hidden files
    (left / ".hidden").write_text("hidden left\n")
    (right / ".hidden").write_text("hidden right\n")

    return left, right


@pytest.fixture
def sample_gitignore(tmp_path: Path) -> Path:
    """Create a directory with a .gitignore file."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".gitignore").write_text("*.pyc\n__pycache__/\n.env\n")
    (root / "keep.py").write_text("keep\n")
    (root / "ignore.pyc").write_text("ignore\n")
    (root / ".env").write_text("SECRET=x\n")
    return root
