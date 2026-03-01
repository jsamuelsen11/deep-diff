"""Tests for deep_diff.git.commands subprocess wrappers."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from deep_diff.git.commands import (
    GitError,
    extract_file,
    find_repo_root,
    list_tree_files,
    validate_ref,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestFindRepoRoot:
    """Tests for find_repo_root."""

    def test_returns_repo_root(self, git_repo: Path) -> None:
        result = find_repo_root(cwd=git_repo)
        assert result == git_repo

    def test_works_from_subdirectory(self, git_repo: Path) -> None:
        subdir = git_repo / "sub"
        result = find_repo_root(cwd=subdir)
        assert result == git_repo

    def test_raises_outside_repo(self, tmp_path: Path) -> None:
        not_a_repo = tmp_path / "empty"
        not_a_repo.mkdir()
        with pytest.raises(GitError, match="Not inside a git repository"):
            find_repo_root(cwd=not_a_repo)


class TestValidateRef:
    """Tests for validate_ref."""

    def test_valid_branch_returns_sha(self, git_repo: Path) -> None:
        sha = validate_ref("main", repo_root=git_repo)
        assert re.fullmatch(r"[0-9a-f]{40}", sha)

    def test_valid_feature_branch(self, git_repo: Path) -> None:
        sha = validate_ref("feature", repo_root=git_repo)
        assert re.fullmatch(r"[0-9a-f]{40}", sha)

    def test_head_resolves(self, git_repo: Path) -> None:
        sha = validate_ref("HEAD", repo_root=git_repo)
        main_sha = validate_ref("main", repo_root=git_repo)
        assert sha == main_sha

    def test_different_branches_different_shas(self, git_repo: Path) -> None:
        main_sha = validate_ref("main", repo_root=git_repo)
        feature_sha = validate_ref("feature", repo_root=git_repo)
        assert main_sha != feature_sha

    def test_invalid_ref_raises(self, git_repo: Path) -> None:
        with pytest.raises(GitError, match="Invalid git ref 'nonexistent'"):
            validate_ref("nonexistent", repo_root=git_repo)

    def test_empty_ref_raises(self, git_repo: Path) -> None:
        with pytest.raises(GitError, match="Invalid git ref"):
            validate_ref("", repo_root=git_repo)


class TestListTreeFiles:
    """Tests for list_tree_files."""

    def test_lists_main_files(self, git_repo: Path) -> None:
        files = list_tree_files("main", repo_root=git_repo)
        assert files == ("file_a.txt", "file_b.txt", "sub/nested.txt")

    def test_lists_feature_files(self, git_repo: Path) -> None:
        files = list_tree_files("feature", repo_root=git_repo)
        assert files == (
            "file_a.txt",
            "file_b.txt",
            "file_c.txt",
            "sub/nested.txt",
        )

    def test_result_is_sorted_tuple(self, git_repo: Path) -> None:
        files = list_tree_files("main", repo_root=git_repo)
        assert isinstance(files, tuple)
        assert list(files) == sorted(files)

    def test_invalid_ref_raises(self, git_repo: Path) -> None:
        with pytest.raises(GitError, match="Failed to list tree"):
            list_tree_files("nonexistent", repo_root=git_repo)


class TestExtractFile:
    """Tests for extract_file."""

    def test_extracts_correct_content(self, git_repo: Path) -> None:
        content = extract_file("main", "file_a.txt", repo_root=git_repo)
        assert content == b"hello\n"

    def test_extracts_modified_content_on_feature(self, git_repo: Path) -> None:
        content = extract_file("feature", "file_a.txt", repo_root=git_repo)
        assert content == b"hello modified\n"

    def test_extracts_nested_file(self, git_repo: Path) -> None:
        content = extract_file("main", "sub/nested.txt", repo_root=git_repo)
        assert content == b"nested content\n"

    def test_nonexistent_path_raises(self, git_repo: Path) -> None:
        with pytest.raises(GitError, match="does not exist at ref"):
            extract_file("main", "no_such_file.txt", repo_root=git_repo)

    def test_file_only_on_feature(self, git_repo: Path) -> None:
        content = extract_file("feature", "file_c.txt", repo_root=git_repo)
        assert content == b"new file\n"

        with pytest.raises(GitError, match="does not exist at ref"):
            extract_file("main", "file_c.txt", repo_root=git_repo)
