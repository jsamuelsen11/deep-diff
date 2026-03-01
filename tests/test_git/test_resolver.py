"""Tests for deep_diff.git.resolver."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from deep_diff.git.commands import GitError
from deep_diff.git.resolver import GitResolver, _sanitize_ref_name, _strip_prefix, is_git_ref

if TYPE_CHECKING:
    from pathlib import Path


class TestIsGitRef:
    """Tests for is_git_ref."""

    def test_git_prefix_detected(self) -> None:
        assert is_git_ref("git:main") is True

    def test_git_prefix_with_slash(self) -> None:
        assert is_git_ref("git:feature/auth") is True

    def test_plain_path_not_detected(self) -> None:
        assert is_git_ref("./path") is False

    def test_relative_path_not_detected(self) -> None:
        assert is_git_ref("src/deep_diff") is False

    def test_empty_string_not_detected(self) -> None:
        assert is_git_ref("") is False

    def test_bare_git_prefix(self) -> None:
        assert is_git_ref("git:") is True


class TestStripPrefix:
    """Tests for _strip_prefix."""

    def test_strips_prefix(self) -> None:
        assert _strip_prefix("git:main") == "main"

    def test_strips_with_slash(self) -> None:
        assert _strip_prefix("git:feature/auth") == "feature/auth"

    def test_bare_prefix_returns_empty(self) -> None:
        assert _strip_prefix("git:") == ""


class TestSanitizeRefName:
    """Tests for _sanitize_ref_name."""

    def test_simple_branch(self) -> None:
        assert _sanitize_ref_name("main") == "main"

    def test_slash_replaced(self) -> None:
        assert _sanitize_ref_name("feature/auth") == "feature_auth"

    def test_tilde_replaced(self) -> None:
        assert _sanitize_ref_name("HEAD~3") == "HEAD_3"

    def test_long_ref_truncated(self) -> None:
        long_ref = "a" * 100
        result = _sanitize_ref_name(long_ref)
        assert len(result) == 50

    def test_empty_returns_ref(self) -> None:
        assert _sanitize_ref_name("") == "ref"


class TestGitResolverContextManager:
    """Tests for GitResolver lifecycle."""

    def test_enter_returns_self(self, git_repo: Path) -> None:
        resolver = GitResolver(cwd=git_repo)
        with resolver as ctx:
            assert ctx is resolver

    def test_cleanup_removes_tmpdirs(self, git_repo: Path) -> None:
        with GitResolver(cwd=git_repo) as resolver:
            left, _ = resolver.resolve_pair("git:main", "git:feature")
            tmpdir_parent = left.parent
            assert tmpdir_parent.exists()
        # After exit, temp dir should be cleaned up
        assert not tmpdir_parent.exists()


class TestGitResolverResolvePair:
    """Tests for resolve_pair."""

    def test_both_git_refs(self, git_repo: Path) -> None:
        with GitResolver(cwd=git_repo) as resolver:
            left, right = resolver.resolve_pair("git:main", "git:feature")
            assert left.is_dir()
            assert right.is_dir()
            # Check files extracted correctly
            assert (left / "file_a.txt").read_text() == "hello\n"
            assert (right / "file_a.txt").read_text() == "hello modified\n"
            assert not (left / "file_c.txt").exists()
            assert (right / "file_c.txt").read_text() == "new file\n"

    def test_nested_files_extracted(self, git_repo: Path) -> None:
        with GitResolver(cwd=git_repo) as resolver:
            left, _ = resolver.resolve_pair("git:main", "git:main")
            assert (left / "sub" / "nested.txt").read_text() == "nested content\n"

    def test_plain_path_passthrough(self, git_repo: Path) -> None:
        with GitResolver(cwd=git_repo) as resolver:
            left, right = resolver.resolve_pair(str(git_repo), str(git_repo))
            # Plain paths should be returned as-is (resolved to Path)
            from pathlib import Path as _Path

            assert left == _Path(str(git_repo))
            assert right == _Path(str(git_repo))

    def test_mixed_git_ref_and_plain_path(self, git_repo: Path) -> None:
        with GitResolver(cwd=git_repo) as resolver:
            left, right = resolver.resolve_pair("git:main", str(git_repo))
            # Left should be a temp dir with extracted files
            assert (left / "file_a.txt").read_text() == "hello\n"
            # Right should be the original path
            from pathlib import Path as _Path

            assert right == _Path(str(git_repo))

    def test_display_name_in_path(self, git_repo: Path) -> None:
        with GitResolver(cwd=git_repo) as resolver:
            left, right = resolver.resolve_pair("git:main", "git:feature")
            assert left.name == "main"
            assert right.name == "feature"

    def test_both_plain_paths_no_git_calls(self, git_repo: Path) -> None:
        with (
            patch("deep_diff.git.resolver.find_repo_root") as mock_root,
            GitResolver(cwd=git_repo) as resolver,
        ):
            resolver.resolve_pair(str(git_repo), str(git_repo))
            mock_root.assert_not_called()

    def test_invalid_ref_raises(self, git_repo: Path) -> None:
        with (
            GitResolver(cwd=git_repo) as resolver,
            pytest.raises(GitError, match="Invalid git ref"),
        ):
            resolver.resolve_pair("git:nonexistent", "git:main")

    def test_not_a_repo_raises(self, tmp_path: Path) -> None:
        not_a_repo = tmp_path / "empty"
        not_a_repo.mkdir()
        with (
            GitResolver(cwd=not_a_repo) as resolver,
            pytest.raises(GitError, match="Not inside a git repository"),
        ):
            resolver.resolve_pair("git:main", "git:main")

    def test_same_ref_both_sides(self, git_repo: Path) -> None:
        with GitResolver(cwd=git_repo) as resolver:
            left, right = resolver.resolve_pair("git:main", "git:main")
            # Both should have identical content but different paths
            assert left != right
            assert (left / "file_a.txt").read_text() == (right / "file_a.txt").read_text()
