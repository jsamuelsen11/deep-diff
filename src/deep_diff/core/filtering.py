"""File filtering: gitignore, glob patterns, hidden files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import TYPE_CHECKING

from pathspec import GitIgnoreSpec

if TYPE_CHECKING:
    from pathlib import Path

GITIGNORE_FILENAME = ".gitignore"
HIDDEN_PREFIX = "."


def _join_posix(directory: str, name: str) -> str:
    """Join a relative directory and name with POSIX separator."""
    if directory:
        return f"{directory}/{name}"
    return name


def _ancestor_dirs(rel_path: str) -> list[str]:
    """Return all ancestor directory prefixes for a relative path.

    For 'a/b/c.txt', returns ['', 'a', 'a/b'].
    For 'file.txt', returns [''].
    """
    parts = rel_path.split("/")
    ancestors: list[str] = [""]
    for i in range(len(parts) - 1):
        ancestors.append("/".join(parts[: i + 1]))
    return ancestors


@dataclass(frozen=True)
class FilterConfig:
    """Immutable configuration for file filtering.

    Controls which files are included or excluded when scanning a directory tree.
    Filters are applied in order: hidden -> gitignore -> include -> exclude.
    """

    respect_gitignore: bool = True
    include_hidden: bool = False
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()


class FileFilter:
    """Filters directory trees using layered rules.

    Filter order: hidden -> gitignore -> include glob -> exclude glob.
    """

    def __init__(self, config: FilterConfig) -> None:
        """Initialize the filter with the given configuration."""
        self._config = config

    def scan(self, root: Path) -> tuple[str, ...]:
        """Walk the directory tree and return filtered relative paths.

        Returns a sorted tuple of POSIX-style relative path strings for all
        files that pass all filter layers.

        Raises:
            NotADirectoryError: If root does not exist or is not a directory.
        """
        if not root.is_dir():
            msg = f"Not a directory: {root}"
            raise NotADirectoryError(msg)

        gitignore_specs: dict[str, GitIgnoreSpec] = {}
        result: list[str] = []

        for dirpath_str, dirnames, filenames in os.walk(root):
            dirpath = root.__class__(dirpath_str)
            rel_dir = dirpath.relative_to(root).as_posix()
            if rel_dir == ".":
                rel_dir = ""

            # Collect .gitignore for this directory (unconditionally, even if hidden)
            if self._config.respect_gitignore:
                gitignore_path = dirpath / GITIGNORE_FILENAME
                if gitignore_path.is_file():
                    lines = gitignore_path.read_text().splitlines()
                    gitignore_specs[rel_dir] = GitIgnoreSpec.from_lines(lines)

            # Layer 1: Prune hidden directories
            if not self._config.include_hidden:
                dirnames[:] = [d for d in dirnames if not self._is_hidden(d)]

            # Layer 2: Prune gitignored directories
            if self._config.respect_gitignore:
                dirnames[:] = [
                    d
                    for d in dirnames
                    if not self._is_gitignored(
                        _join_posix(rel_dir, d),
                        is_dir=True,
                        gitignore_specs=gitignore_specs,
                    )
                ]

            # Sort for deterministic traversal order
            dirnames.sort()

            for filename in filenames:
                rel_path = _join_posix(rel_dir, filename)

                # Layer 1: Hidden file check
                if not self._config.include_hidden and self._is_hidden(filename):
                    continue

                # Layer 2: Gitignore check
                if self._config.respect_gitignore and self._is_gitignored(
                    rel_path,
                    is_dir=False,
                    gitignore_specs=gitignore_specs,
                ):
                    continue

                # Layer 3: Include patterns (allowlist)
                if not self._matches_include(rel_path):
                    continue

                # Layer 4: Exclude patterns (blocklist)
                if self._matches_exclude(rel_path):
                    continue

                result.append(rel_path)

        result.sort()
        return tuple(result)

    @staticmethod
    def _is_hidden(name: str) -> bool:
        """Check if a file or directory name is hidden (starts with '.')."""
        return name.startswith(HIDDEN_PREFIX)

    @staticmethod
    def _is_gitignored(
        relative_path: str,
        *,
        is_dir: bool,
        gitignore_specs: dict[str, GitIgnoreSpec],
    ) -> bool:
        """Check if a path is matched by any applicable .gitignore spec."""
        if not gitignore_specs:
            return False
        check_suffix = "/" if is_dir else ""
        for ancestor in _ancestor_dirs(relative_path):
            spec = gitignore_specs.get(ancestor)
            if spec is None:
                continue
            local_path = relative_path[len(ancestor) + 1 :] if ancestor else relative_path
            if spec.match_file(local_path + check_suffix):
                return True
        return False

    def _matches_include(self, relative_path: str) -> bool:
        """Check if path matches any include pattern. True if no patterns defined."""
        if not self._config.include_patterns:
            return True
        return any(fnmatch(relative_path, p) for p in self._config.include_patterns)

    def _matches_exclude(self, relative_path: str) -> bool:
        """Check if path matches any exclude pattern. False if no patterns defined."""
        if not self._config.exclude_patterns:
            return False
        return any(fnmatch(relative_path, p) for p in self._config.exclude_patterns)
