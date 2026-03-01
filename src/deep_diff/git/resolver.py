"""GitResolver: resolves git refs to temporary directory paths."""

from __future__ import annotations

import re
import tempfile
from typing import TYPE_CHECKING

from deep_diff.git.commands import (
    extract_file,
    find_repo_root,
    list_tree_files,
    validate_ref,
)

if TYPE_CHECKING:
    from pathlib import Path

_GIT_PREFIX = "git:"
_UNSAFE_CHARS = re.compile(r"[^\w\-.]")


def is_git_ref(value: str) -> bool:
    """Return True if the value uses the git: prefix."""
    return value.startswith(_GIT_PREFIX)


def _strip_prefix(value: str) -> str:
    """Strip the 'git:' prefix and return the bare ref."""
    return value[len(_GIT_PREFIX) :]


def _sanitize_ref_name(ref: str) -> str:
    """Create a filesystem-safe directory name from a git ref.

    Replaces unsafe characters with underscores and truncates to a
    reasonable length for use as a directory name.
    """
    safe = _UNSAFE_CHARS.sub("_", ref)
    return safe[:50] or "ref"


class GitResolver:
    """Resolves one or two git refs to temporary directory paths.

    Extracts file trees from git history into TemporaryDirectory
    instances, then yields the resolved Path objects. Cleanup is
    automatic when the context manager exits.

    Usage::

        with GitResolver(cwd=Path(".")) as resolver:
            left_path, right_path = resolver.resolve_pair("git:main", "git:feature")
            result = Comparator(...).compare(left_path, right_path)

    Plain filesystem paths (no ``git:`` prefix) are returned unchanged.
    """

    def __init__(self, *, cwd: Path | None = None) -> None:
        self._cwd = cwd
        self._tmpdirs: list[tempfile.TemporaryDirectory[str]] = []
        self._repo_root: Path | None = None

    def __enter__(self) -> GitResolver:
        return self

    def __exit__(self, *args: object) -> None:
        for tmpdir in self._tmpdirs:
            tmpdir.cleanup()
        self._tmpdirs.clear()

    def resolve_pair(self, left: str, right: str) -> tuple[Path, Path]:
        """Resolve a pair of arguments to filesystem paths.

        Each argument is either a ``git:<ref>`` string (extracted to a
        temp directory) or a plain filesystem path (returned as-is).

        Args:
            left: Left argument.
            right: Right argument.

        Returns:
            Tuple of (left_path, right_path) ready for Comparator.

        Raises:
            GitError: If git operations fail.
        """
        left_path = self._resolve_single(left)
        right_path = self._resolve_single(right)
        return left_path, right_path

    def _resolve_single(self, value: str) -> Path:
        """Resolve one argument to a Path."""
        from pathlib import Path as _Path

        if not is_git_ref(value):
            return _Path(value)

        ref = _strip_prefix(value)
        repo_root = self._get_repo_root()
        validated_sha = validate_ref(ref, repo_root=repo_root)
        return self._extract_to_tmpdir(
            validated_sha,
            display_name=_sanitize_ref_name(ref),
            repo_root=repo_root,
        )

    def _get_repo_root(self) -> Path:
        """Lazily discover and cache the repo root."""
        if self._repo_root is None:
            self._repo_root = find_repo_root(self._cwd)
        return self._repo_root

    def _extract_to_tmpdir(
        self,
        ref: str,
        *,
        display_name: str,
        repo_root: Path,
    ) -> Path:
        """Extract git tree files into a new temporary directory.

        Creates a named subdirectory inside the temp dir so that
        ``Path.name`` reflects the ref for display in renderers.
        """
        from pathlib import Path as _Path

        tmpdir = tempfile.TemporaryDirectory(prefix="deep-diff-git-")
        self._tmpdirs.append(tmpdir)

        named_subdir = _Path(tmpdir.name) / display_name
        named_subdir.mkdir()

        files = list_tree_files(ref, repo_root=repo_root)

        for rel_path in files:
            content = extract_file(ref, rel_path, repo_root=repo_root)
            dest = named_subdir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

        return named_subdir
