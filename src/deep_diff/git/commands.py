"""Low-level git subprocess wrappers.

Security notes
--------------
All subprocess calls use list-form arguments with ``shell=False`` (the
default, but set explicitly for clarity).  This prevents shell injection.

User-supplied values (refs, paths) are validated by ``_reject_option_like``
before being passed to git, which prevents flag-injection attacks (e.g. a
ref named ``--upload-pack=…`` being interpreted as a git option).  Where
git supports it, ``--`` end-of-options markers are also used as a defence-
in-depth measure.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class GitError(Exception):
    """Raised when a git operation fails or the environment is invalid."""


def _reject_option_like(value: str, *, label: str) -> None:
    """Raise ``GitError`` if *value* looks like a CLI option.

    Git interprets strings starting with ``-`` as flags.  Rejecting them
    up-front prevents flag-injection regardless of how the value is later
    interpolated into a command list.
    """
    if value.startswith("-"):
        msg = f"{label} must not start with '-': {value!r}"
        raise GitError(msg)


def find_repo_root(cwd: Path | None = None) -> Path:
    """Return the absolute path to the git repo root.

    Args:
        cwd: Working directory to search from. Defaults to process cwd.

    Raises:
        GitError: If not inside a git repository.
    """
    from pathlib import Path as _Path

    cmd = ["git", "rev-parse", "--show-toplevel"]
    cwd_str = str(cwd) if cwd is not None else None
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd_str,
        shell=False,
    )
    if result.returncode != 0:
        msg = "Not inside a git repository"
        if cwd is not None:
            msg = f"{msg}: {cwd}"
        raise GitError(msg)
    return _Path(result.stdout.strip())


def validate_ref(ref: str, *, repo_root: Path) -> str:
    """Resolve and validate a git ref to its full SHA.

    Args:
        ref: Branch, tag, commit, or expression like HEAD~2.
        repo_root: Absolute path to the git repo root.

    Returns:
        Full 40-character SHA of the resolved ref.

    Raises:
        GitError: If the ref cannot be resolved.
    """
    _reject_option_like(ref, label="Git ref")
    cmd = ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        shell=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = f"Invalid git ref '{ref}'"
        if stderr:
            msg = f"{msg}: {stderr}"
        raise GitError(msg)
    return result.stdout.strip()


def list_tree_files(ref: str, *, repo_root: Path) -> tuple[str, ...]:
    """List all files in a git tree at the given ref.

    Submodule entries (mode 160000) are filtered out.

    Args:
        ref: Validated git ref (SHA or symbolic).
        repo_root: Absolute path to the git repo root.

    Returns:
        Sorted tuple of POSIX-style relative paths.

    Raises:
        GitError: If the git command fails.
    """
    _reject_option_like(ref, label="Git ref")
    # -- separates options from the tree-ish argument
    cmd = ["git", "ls-tree", "-r", "--", ref]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        shell=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = f"Failed to list tree at ref '{ref}'"
        if stderr:
            msg = f"{msg}: {stderr}"
        raise GitError(msg)

    files: list[str] = []
    for line in result.stdout.splitlines():
        # Format: <mode> <type> <hash>\t<path>
        if not line:
            continue
        meta, _, path = line.partition("\t")
        mode = meta.split()[0]
        # Skip submodule entries (mode 160000)
        if mode == "160000":
            continue
        files.append(path)

    return tuple(sorted(files))


def extract_file(ref: str, path_in_repo: str, *, repo_root: Path) -> bytes:
    """Return the raw bytes of a file at a given ref.

    Args:
        ref: Validated git ref.
        path_in_repo: POSIX path of the file relative to the repo root.
        repo_root: Absolute path to the git repo root.

    Returns:
        File contents as bytes.

    Raises:
        GitError: If the path does not exist at that ref.
    """
    _reject_option_like(ref, label="Git ref")
    _reject_option_like(path_in_repo, label="Path")
    cmd = ["git", "show", f"{ref}:{path_in_repo}"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        cwd=str(repo_root),
        shell=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        msg = f"Path '{path_in_repo}' does not exist at ref '{ref}'"
        if stderr:
            msg = f"{msg}: {stderr}"
        raise GitError(msg)
    return result.stdout
