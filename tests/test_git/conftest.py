"""Shared fixtures for git integration tests."""

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
