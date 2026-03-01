"""Shared test fixtures for deep-diff."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _run_git(repo: Path, *args: str) -> None:
    """Run a git command inside the given repo."""
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )


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
def sample_text_files(tmp_path: Path) -> tuple[Path, Path]:
    """Create two text files with a known single-line difference.

    Left:  line 1 / line 2 / line 3
    Right: line 1 / changed line 2 / line 3
    """
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("line 1\nline 2\nline 3\n")
    right.write_text("line 1\nchanged line 2\nline 3\n")
    return left, right


@pytest.fixture
def binary_files(tmp_path: Path) -> tuple[Path, Path]:
    """Create two different binary files containing null bytes."""
    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    right.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00")
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


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repository with two branches.

    Layout after setup:

    main branch:
        file_a.txt  -> "hello\\n"
        file_b.txt  -> "world\\n"
        sub/nested.txt -> "nested content\\n"

    feature branch (branched from main):
        file_a.txt  -> "hello modified\\n"  (modified)
        file_b.txt  -> "world\\n"           (unchanged)
        file_c.txt  -> "new file\\n"        (added)
        sub/nested.txt -> "nested content\\n" (unchanged)

    Returns the repo root path. Current branch is main after setup.
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    _run_git(repo, "init", "--initial-branch=main")
    _run_git(repo, "config", "user.email", "test@test.com")
    _run_git(repo, "config", "user.name", "Test")

    # First commit on main
    (repo / "file_a.txt").write_text("hello\n")
    (repo / "file_b.txt").write_text("world\n")
    (repo / "sub").mkdir()
    (repo / "sub" / "nested.txt").write_text("nested content\n")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")

    # Create feature branch with changes
    _run_git(repo, "checkout", "-b", "feature")
    (repo / "file_a.txt").write_text("hello modified\n")
    (repo / "file_c.txt").write_text("new file\n")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "feature change")

    # Return to main
    _run_git(repo, "checkout", "main")

    return repo
